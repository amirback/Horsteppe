import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { isAdminReady } from "@/lib/supabase/env";
import { isUuid } from "@/lib/ids";

/**
 * Сколько запусков сборщика допускается на один проект за всю его жизнь.
 *
 * Раньше повтор обнулял счётчик попыток задачи, и повторов было сколько
 * угодно: каждый запускал сборщик заново, каждый мог заплатить провайдерам.
 * Теперь счётчик копится, повтор добавляет один раунд, а потолок общий.
 * По умолчанию 8: исходные две попытки плюс три повтора по два.
 */
const ATTEMPTS_CAP = Number(process.env.MAX_ATTEMPTS_PER_PROJECT ?? 8);
/** Сколько попыток добавляет одно нажатие — столько же, сколько у новой задачи. */
const ATTEMPTS_PER_RETRY = 2;

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
  if (!isUuid(id)) {
    return NextResponse.json({ error: "not_found" }, { status: 404 });
  }

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

  const { data: job } = await admin
    .from("jobs")
    .select("id, attempts")
    .eq("project_id", id)
    .maybeSingle();
  if (!job) {
    // Проект упал до постановки в очередь — задачи нет, повторять нечего.
    return NextResponse.json({ error: "queue_failed" }, { status: 409 });
  }
  const attempts = Number(job.attempts) || 0;
  if (attempts >= ATTEMPTS_CAP) {
    return NextResponse.json({ error: "retry_limit" }, { status: 429 });
  }

  // Сначала проект, потом задача. В обратном порядке сборщик мог успеть
  // взять задачу и написать «Пишем сценарий…», а мы затёрли бы это своим
  // «В очереди…». Сборщик берёт только задачи, так что проект в очереди без
  // задачи в очереди ничего не запускает.
  const { error: projectError } = await admin
    .from("projects")
    .update({ status: "queued", status_detail: "В очереди…", error_message: null })
    .eq("id", id)
    .eq("status", "failed"); // второй клик не перезапишет уже идущую сборку
  if (projectError) {
    console.error("project requeue failed:", projectError.message);
    return NextResponse.json({ error: "queue_failed" }, { status: 500 });
  }

  // Счётчик попыток НЕ обнуляется: повтор добавляет раунд, а не открывает
  // бесконечность.
  const { error: jobError } = await admin
    .from("jobs")
    .update({
      status: "queued",
      max_attempts: Math.min(attempts + ATTEMPTS_PER_RETRY, ATTEMPTS_CAP),
      run_after: new Date().toISOString(),
      locked_at: null,
      locked_by: null,
      last_error: null,
    })
    .eq("id", job.id);
  if (jobError) {
    console.error("job requeue failed:", jobError.message);
    await admin
      .from("projects")
      .update({ status: "failed", status_detail: null, error_message: "Ошибка постановки в очередь" })
      .eq("id", id);
    return NextResponse.json({ error: "queue_failed" }, { status: 500 });
  }

  return NextResponse.json({ ok: true });
}
