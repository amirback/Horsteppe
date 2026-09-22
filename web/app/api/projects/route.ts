import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { isAdminReady, isBackendReady } from "@/lib/supabase/env";

const STYLES = ["cinematic", "documentary", "explainer", "product", "anime"];
const LIST_LIMIT = 50;

/** Список проектов пользователя. Политики доступа отдают только его собственные. */
export async function GET() {
  if (!isBackendReady()) {
    return NextResponse.json({ error: "backend_not_configured" }, { status: 503 });
  }

  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const { data, error } = await supabase
    .from("projects")
    .select("id, topic, style, duration_sec, aspect_ratio, status, status_detail, cost_usd, created_at")
    .order("created_at", { ascending: false })
    .limit(LIST_LIMIT);

  if (error) {
    return NextResponse.json({ error: "query_failed" }, { status: 500 });
  }

  const projects = data ?? [];
  return NextResponse.json({
    projects,
    counts: {
      total: projects.length,
      active: projects.filter((p) => p.status === "queued" || p.status === "generating").length,
      done: projects.filter((p) => p.status === "done").length,
      failed: projects.filter((p) => p.status === "failed").length,
    },
  });
}
const FORMATS = ["9:16", "16:9", "1:1", "4:5"];
const PROJECT_TYPES = ["general_video", "product_ad", "image_to_video"];
const BUCKET = "media";
const MAX_REFERENCES = 5;
// Потолок расходов задаёт человек, но сверху он ограничен и здесь: опечатка
// в поле ввода не должна превращаться в счёт на тысячу долларов.
const MAX_BUDGET_USD = 20;

type StagedFile = {
  path: string;
  mime_type: string;
  width: number;
  height: number;
  bytes: number;
};

/**
 * Файлы приходят из /api/uploads и лежат в личном отстойнике. Путь — это
 * данные от клиента, поэтому проверяется, что он ведёт в отстойник именно
 * этого человека: иначе чужой снимок можно было бы прицепить к своему проекту.
 */
function ownStagedFiles(raw: unknown, userId: string): StagedFile[] | null {
  if (!Array.isArray(raw)) return [];
  if (raw.length > MAX_REFERENCES) return null;
  const prefix = `staging/${userId}/`;
  const files: StagedFile[] = [];
  for (const item of raw) {
    const path = typeof item?.path === "string" ? item.path : "";
    if (!path.startsWith(prefix) || path.includes("..")) return null;
    files.push({
      path,
      mime_type: typeof item?.mime_type === "string" ? item.mime_type : "image/jpeg",
      width: Number(item?.width) || 0,
      height: Number(item?.height) || 0,
      bytes: Number(item?.bytes) || 0,
    });
  }
  return files;
}

/**
 * Пометить проект несостоявшимся.
 *
 * Любой сбой ПОСЛЕ создания строки проекта обязан оставить его в конечном
 * состоянии. Иначе проект висит «в очереди» вечно: задачи у него нет, значит
 * сборщик его никогда не возьмёт, — но он считается активным и по лимиту
 * одновременных работ блокирует человеку создание новых. Сообщение при этом
 * отправляет смотреть на страницу «Мои видео», где ничего не происходит.
 */
async function failProject(
  admin: ReturnType<typeof createAdminClient>, id: string, message: string
): Promise<void> {
  const { error } = await admin
    .from("projects")
    .update({ status: "failed", error_message: message, status_detail: null })
    .eq("id", id);
  if (error) {
    // Больше сделать нечего, но молчать нельзя: такой проект и есть тот
    // самый вечный «в очереди», и в логе должно остаться, откуда он взялся.
    console.error("could not mark project failed:", id, error.message);
  }
}

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
    project_type?: string;
    brief?: Record<string, unknown>;
    max_budget_usd?: number;
    references?: unknown;
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

  const projectType = PROJECT_TYPES.includes(body.project_type ?? "")
    ? body.project_type!
    : "general_video";

  const staged = ownStagedFiles(body.references, user.id);
  if (staged === null) {
    return NextResponse.json({ error: "invalid_references" }, { status: 400 });
  }

  // Требования режимов. Реклама без названия товара и оживление без снимка —
  // это не «почти готовый заказ», а заказ, который нечем выполнить.
  const brief = (body.brief ?? {}) as Record<string, unknown>;
  if (projectType === "product_ad" && !String(brief.product_name ?? "").trim()) {
    return NextResponse.json({ error: "product_name_required" }, { status: 400 });
  }
  if (projectType === "image_to_video" && staged.length === 0) {
    return NextResponse.json({ error: "photo_required" }, { status: 400 });
  }

  let maxBudget: number | null = null;
  if (body.max_budget_usd !== undefined && body.max_budget_usd !== null) {
    const value = Number(body.max_budget_usd);
    if (!Number.isFinite(value) || value < 0 || value > MAX_BUDGET_USD) {
      return NextResponse.json({ error: "invalid_budget", limit: MAX_BUDGET_USD }, { status: 400 });
    }
    maxBudget = value;
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
      project_type: projectType,
      brief,
      max_budget_usd: maxBudget,
      status: "queued",
      status_detail: "В очереди…",
    })
    .select()
    .single();
  if (projectError || !project) {
    console.error("project insert failed:", projectError?.message);
    return NextResponse.json({ error: "create_failed" }, { status: 500 });
  }

  // Снимки переезжают из отстойника в каталог проекта только теперь, когда
  // проект существует. Публичная ссылка нужна потому, что её получает
  // провайдер image-to-video: подписанная ссылка истекает раньше, чем
  // заканчивается генерация.
  if (staged.length > 0) {
    const rows = [];
    for (const [index, file] of staged.entries()) {
      const ext = file.path.split(".").pop() || "jpg";
      const destination = `projects/${project.id}/references/${index}.${ext}`;
      const { error: moveError } = await admin.storage.from(BUCKET).move(file.path, destination);
      if (moveError) {
        console.error("reference move failed:", moveError.message);
        await failProject(admin, project.id, "Не удалось сохранить фотографии");
        return NextResponse.json({ error: "reference_move_failed" }, { status: 500 });
      }
      const { data: published } = admin.storage.from(BUCKET).getPublicUrl(destination);
      rows.push({
        project_id: project.id,
        order_index: index,
        is_primary: index === 0,
        storage_path: destination,
        public_url: published.publicUrl,
        mime_type: file.mime_type,
        width: file.width,
        height: file.height,
        bytes: file.bytes,
      });
    }
    const { error: referenceError } = await admin.from("project_references").insert(rows);
    if (referenceError) {
      console.error("reference insert failed:", referenceError.message);
      await failProject(admin, project.id, "Не удалось прикрепить фотографии");
      return NextResponse.json({ error: "reference_save_failed" }, { status: 500 });
    }
  }

  const { error: jobError } = await admin.from("jobs").insert({ project_id: project.id });
  if (jobError) {
    console.error("job insert failed:", jobError.message);
    await failProject(admin, project.id, "Ошибка постановки в очередь");
    return NextResponse.json({ error: "queue_failed" }, { status: 500 });
  }

  return NextResponse.json({ id: project.id }, { status: 201 });
}
