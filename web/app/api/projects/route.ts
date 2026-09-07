import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { isAdminReady } from "@/lib/supabase/env";

const STYLES = ["cinematic", "documentary", "explainer", "product", "anime"];
const FORMATS = ["9:16", "16:9", "1:1", "4:5"];

/**
 * Постановка проекта в производство.
 *
 * Ошибки возвращаются машинными кодами, а не текстом: сайт трёхъязычный,
 * и перевод должен жить на клиенте, а не в API.
 */
export async function POST(request: Request) {
  if (!isAdminReady()) {
    return NextResponse.json({ error: "backend_not_configured" }, { status: 503 });
  }

  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  let body: {
    topic?: string;
    style?: string;
    duration_sec?: number;
    aspect_ratio?: string;
  };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "invalid_request" }, { status: 400 });
  }

  const topic = (body.topic ?? "").trim();
  if (topic.length < 8) {
    return NextResponse.json({ error: "topic_too_short" }, { status: 400 });
  }
  if (topic.length > 500) {
    return NextResponse.json({ error: "topic_too_long" }, { status: 400 });
  }

  const style = STYLES.includes(body.style ?? "") ? body.style! : "cinematic";
  const aspect = FORMATS.includes(body.aspect_ratio ?? "") ? body.aspect_ratio! : "9:16";
  // Ограничения совпадают с проверкой в схеме базы (10..60), иначе insert упадёт.
  const duration = Math.min(60, Math.max(10, Number(body.duration_sec) || 30));

  const admin = createAdminClient();

  // Лимиты защищают бюджет от случайного или намеренного выжигания.
  const maxConcurrent = Number(process.env.MAX_CONCURRENT_PER_USER ?? 1);
  const maxDaily = Number(process.env.MAX_DAILY_PER_USER ?? 5);

  const { count: activeCount } = await admin
    .from("projects")
    .select("id", { count: "exact", head: true })
    .eq("user_id", user.id)
    .in("status", ["queued", "generating"]);
  if ((activeCount ?? 0) >= maxConcurrent) {
    return NextResponse.json({ error: "rate_limit_concurrent" }, { status: 429 });
  }

  const dayAgo = new Date(Date.now() - 24 * 3600 * 1000).toISOString();
  const { count: dailyCount } = await admin
    .from("projects")
    .select("id", { count: "exact", head: true })
    .eq("user_id", user.id)
    .gte("created_at", dayAgo);
  if ((dailyCount ?? 0) >= maxDaily) {
    return NextResponse.json(
      { error: "rate_limit_daily", limit: maxDaily },
      { status: 429 }
    );
  }

  const { data: project, error: projectError } = await admin
    .from("projects")
    .insert({
      user_id: user.id,
      topic,
      style,
      duration_sec: duration,
      aspect_ratio: aspect,
      status: "queued",
      status_detail: "В очереди…",
    })
    .select()
    .single();
  if (projectError || !project) {
    console.error("project insert failed:", projectError?.message);
    return NextResponse.json({ error: "create_failed" }, { status: 500 });
  }

  const { error: jobError } = await admin.from("jobs").insert({ project_id: project.id });
  if (jobError) {
    console.error("job insert failed:", jobError.message);
    await admin
      .from("projects")
      .update({ status: "failed", error_message: "Ошибка постановки в очередь" })
      .eq("id", project.id);
    return NextResponse.json({ error: "queue_failed" }, { status: 500 });
  }

  return NextResponse.json({ id: project.id }, { status: 201 });
}
