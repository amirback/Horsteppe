import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { isAdminReady } from "@/lib/supabase/env";

/**
 * Повторная постановка упавшего проекта в очередь.
 *
 * Кнопка «Попробовать снова» раньше была обычной ссылкой на главную: человек
 * нажимал её и оказывался на первом экране, а проект оставался лежать
 * упавшим. Повтор дешёвый — воркер пропускает всё, что уже собрано, и
 * переделывает только недостающее.
 */
export async function POST(_request: Request, context: { params: Promise<{ id: string }> }) {
  if (!isAdminReady()) {
    return NextResponse.json({ error: "backend_not_configured" }, { status: 503 });
  }

  const { id } = await context.params;

  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  // Читаем через пользовательский клиент: политики доступа сами не отдадут
  // чужой проект, и проверять принадлежность вручную не нужно.
  const { data: project } = await supabase
    .from("projects")
    .select("id, status")
    .eq("id", id)
    .maybeSingle();
  if (!project) {
    return NextResponse.json({ error: "not_found" }, { status: 404 });
  }
  if (project.status !== "failed") {
    return NextResponse.json({ error: "retry_not_failed" }, { status: 409 });
  }

  const admin = createAdminClient();

  // Тот же предохранитель, что и при создании: один проект в работе на
  // человека. Иначе повтор становится дырой в защите бюджета.
  const maxConcurrent = Number(process.env.MAX_CONCURRENT_PER_USER ?? 1);
  const { count: activeCount } = await admin
    .from("projects")
    .select("id", { count: "exact", head: true })
    .eq("user_id", user.id)
    .in("status", ["queued", "generating"]);
  if ((activeCount ?? 0) >= maxConcurrent) {
    return NextResponse.json({ error: "rate_limit_concurrent" }, { status: 429 });
  }

  // Задача на проект одна — `jobs.project_id` уникален, поэтому обновляем
  // существующую строку, а не вставляем вторую.
  const { error: jobError } = await admin
    .from("jobs")
    .update({
      status: "queued",
      attempts: 0,
      run_after: new Date().toISOString(),
      locked_at: null,
      locked_by: null,
      last_error: null,
    })
    .eq("project_id", id);
  if (jobError) {
    console.error("job requeue failed:", jobError.message);
    return NextResponse.json({ error: "queue_failed" }, { status: 500 });
  }

  const { error: projectError } = await admin
    .from("projects")
    .update({ status: "queued", status_detail: "В очереди…", error_message: null })
    .eq("id", id);
  if (projectError) {
    console.error("project requeue failed:", projectError.message);
    return NextResponse.json({ error: "queue_failed" }, { status: 500 });
  }

  return NextResponse.json({ ok: true });
}
