import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const supabase = await createClient();

  // RLS guarantees users only see their own projects.
  const { data: project, error } = await supabase
    .from("projects")
    .select("id, topic, style, duration_sec, status, status_detail, error_message, cost_usd, created_at")
    .eq("id", id)
    .maybeSingle();

  if (error) {
    return NextResponse.json({ error: "Ошибка запроса" }, { status: 500 });
  }
  if (!project) {
    return NextResponse.json({ error: "Проект не найден" }, { status: 404 });
  }

  const [{ data: scenes }, { data: renders }] = await Promise.all([
    supabase
      .from("scenes")
      .select("order_index, narration, status, image_url")
      .eq("project_id", id)
      .order("order_index"),
    supabase
      .from("renders")
      .select("final_video_url, duration_sec, created_at")
      .eq("project_id", id)
      .order("created_at", { ascending: false })
      .limit(1),
  ]);

  return NextResponse.json({
    project,
    scenes: scenes ?? [],
    render: renders?.[0] ?? null,
  });
}
