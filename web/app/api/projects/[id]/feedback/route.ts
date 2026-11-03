import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { isAdminReady } from "@/lib/supabase/env";
import { isUuid } from "@/lib/ids";
import { isMissingTable, parseFeedback, summarizeSources } from "@/app/lib/feedback";

type Params = { params: Promise<{ id: string }> };

/**
 * Свой проект — или ничего. Читаем через пользовательский клиент: политики
 * доступа сами не отдадут чужой проект, и проверять владельца вручную не нужно.
 */
async function ownProject(id: string) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return { error: NextResponse.json({ error: "unauthorized" }, { status: 401 }) };
  if (!isUuid(id)) return { error: NextResponse.json({ error: "not_found" }, { status: 404 }) };
  const { data: project } = await supabase
    .from("projects")
    .select(
      "id, status, style, duration_sec, aspect_ratio, project_type, brief, cost_usd, " +
        "real_video_coverage, degraded_reason"
    )
    .eq("id", id)
    .maybeSingle();
  if (!project) return { error: NextResponse.json({ error: "not_found" }, { status: 404 }) };
  return { user, project: project as unknown as Record<string, unknown> };
}

/** Оценка этого человека для этого проекта. */
export async function GET(_request: Request, { params }: Params) {
  if (!isAdminReady()) {
    return NextResponse.json({ error: "backend_not_configured" }, { status: 503 });
  }
  const { id } = await params;
  const own = await ownProject(id);
  if ("error" in own) return own.error;

  const admin = createAdminClient();
  const { data, error } = await admin
    .from("project_feedback")
    .select("rating, reasons, comment, updated_at")
    .eq("project_id", id)
    .eq("user_id", own.user.id)
    .maybeSingle();
  if (error) {
    if (isMissingTable(error)) {
      return NextResponse.json({ error: "feedback_unavailable" }, { status: 503 });
    }
    console.error("feedback read failed:", error.message);
    return NextResponse.json({ error: "query_failed" }, { status: 500 });
  }
  return NextResponse.json({ feedback: data ?? null });
}

/**
 * Сохранить оценку. Повторная оценка заменяет прежнюю: человек передумал —
 * верим последнему слову.
 *
 * Снимок генерации собирает сервер из базы: модели и провайдеры клипов,
 * формат, длительность, покрытие. Браузеру в этом не доверяем — данные
 * нужны для честного разбора, какая модель что даёт.
 */
export async function POST(request: Request, { params }: Params) {
  if (!isAdminReady()) {
    return NextResponse.json({ error: "backend_not_configured" }, { status: 503 });
  }
  const { id } = await params;
  const own = await ownProject(id);
  if ("error" in own) return own.error;
  const { user, project } = own;

  if (project.status !== "done" && project.status !== "done_degraded") {
    return NextResponse.json({ error: "feedback_not_ready" }, { status: 409 });
  }

  let raw: unknown;
  try {
    raw = await request.json();
  } catch {
    return NextResponse.json({ error: "invalid_feedback" }, { status: 400 });
  }
  const feedback = parseFeedback(raw);
  if (!feedback) {
    return NextResponse.json({ error: "invalid_feedback" }, { status: 400 });
  }

  const admin = createAdminClient();
  const [{ data: renders }, { data: shots }] = await Promise.all([
    admin
      .from("renders")
      .select("id, duration_sec, created_at")
      .eq("project_id", id)
      .order("created_at", { ascending: false })
      .limit(1),
    admin.from("shots").select("provider, model, generation_mode").eq("project_id", id),
  ]);
  const render = renders?.[0] ?? null;
  const brief = (project.brief ?? {}) as Record<string, unknown>;
  const context = {
    render_id: render?.id ?? null,
    render_duration_sec: render?.duration_sec ?? null,
    requested_duration_sec: project.duration_sec,
    style: project.style,
    aspect_ratio: project.aspect_ratio,
    project_type: project.project_type,
    voiceover: brief.voiceover !== false,
    status: project.status,
    real_video_coverage: project.real_video_coverage,
    degraded_reason: project.degraded_reason,
    cost_usd: project.cost_usd,
    shots: shots?.length ?? 0,
    video_sources: summarizeSources(shots ?? []),
  };

  const { data, error } = await admin
    .from("project_feedback")
    .upsert(
      {
        project_id: id,
        user_id: user.id,
        render_id: render?.id ?? null,
        rating: feedback.rating,
        reasons: feedback.reasons,
        comment: feedback.comment,
        context,
      },
      { onConflict: "project_id,user_id" }
    )
    .select("rating, reasons, comment, updated_at")
    .single();
  if (error) {
    if (isMissingTable(error)) {
      return NextResponse.json({ error: "feedback_unavailable" }, { status: 503 });
    }
    console.error("feedback save failed:", error.message);
    return NextResponse.json({ error: "feedback_save_failed" }, { status: 500 });
  }
  return NextResponse.json({ feedback: data });
}
