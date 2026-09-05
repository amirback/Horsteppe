import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";

const STYLES = ["cinematic", "anime", "documentary", "cyberpunk", "watercolor"];

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    return NextResponse.json({ error: "Не авторизован" }, { status: 401 });
  }

  let body: { topic?: string; style?: string; duration_sec?: number };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Некорректный запрос" }, { status: 400 });
  }

  const topic = (body.topic ?? "").trim();
  const style = STYLES.includes(body.style ?? "") ? body.style! : "cinematic";
  const duration = Math.min(60, Math.max(10, Number(body.duration_sec) || 30));

  if (topic.length < 3 || topic.length > 500) {
    return NextResponse.json(
      { error: "Тема должна быть от 3 до 500 символов" },
      { status: 400 }
    );
  }

  const admin = createAdminClient();

  // Rate limits: protect the AI budget from accidental (or deliberate) burn.
  const maxConcurrent = Number(process.env.MAX_CONCURRENT_PER_USER ?? 1);
  const maxDaily = Number(process.env.MAX_DAILY_PER_USER ?? 5);

  const { count: activeCount } = await admin
    .from("projects")
    .select("id", { count: "exact", head: true })
    .eq("user_id", user.id)
    .in("status", ["queued", "generating"]);
  if ((activeCount ?? 0) >= maxConcurrent) {
    return NextResponse.json(
      { error: "У вас уже генерируется видео. Дождитесь завершения." },
      { status: 429 }
    );
  }

  const dayAgo = new Date(Date.now() - 24 * 3600 * 1000).toISOString();
  const { count: dailyCount } = await admin
    .from("projects")
    .select("id", { count: "exact", head: true })
    .eq("user_id", user.id)
    .gte("created_at", dayAgo);
  if ((dailyCount ?? 0) >= maxDaily) {
    return NextResponse.json(
      { error: `Лимит ${maxDaily} видео в сутки исчерпан.` },
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
      status: "queued",
      status_detail: "В очереди…",
    })
    .select()
    .single();
  if (projectError || !project) {
    console.error("project insert failed:", projectError);
    return NextResponse.json({ error: "Не удалось создать проект" }, { status: 500 });
  }

  const { error: jobError } = await admin
    .from("jobs")
    .insert({ project_id: project.id });
  if (jobError) {
    console.error("job insert failed:", jobError);
    await admin
      .from("projects")
      .update({ status: "failed", error_message: "Ошибка постановки в очередь" })
      .eq("id", project.id);
    return NextResponse.json({ error: "Не удалось поставить задачу в очередь" }, { status: 500 });
  }

  return NextResponse.json({ id: project.id }, { status: 201 });
}
