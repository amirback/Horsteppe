import type { createAdminClient } from "@/lib/supabase/admin";

/**
 * Кредиты на ролики: один кредит — одна успешная генерация.
 *
 * Правила денег держит база (миграция 0007): зачисление ровно один раз,
 * баланс не уходит в минус, резерв на время сборки, списание при «Готово» и
 * возврат при ошибке делает триггер на статусе проекта. Здесь — только вызовы.
 *
 * До применения миграции сайт работает как раньше, без кредитов: функции и
 * таблиц ещё нет, и это не ошибка, а «старый режим».
 */

type Admin = ReturnType<typeof createAdminClient>;

export const TIERS = ["economy", "medium", "premium"] as const;
export type Tier = (typeof TIERS)[number];

export function isTier(value: unknown): value is Tier {
  return typeof value === "string" && (TIERS as readonly string[]).includes(value);
}

/** Почты администраторов — переменная ADMIN_EMAILS на Vercel, через запятую. */
export function isAdminEmail(email: string | null | undefined): boolean {
  if (!email) return false;
  const list = (process.env.ADMIN_EMAILS ?? "")
    .split(",")
    .map((item) => item.trim().toLowerCase())
    .filter(Boolean);
  return list.includes(email.trim().toLowerCase());
}

/**
 * Ответ базы «такой таблицы или функции нет» — миграция 0007 не применена.
 * PostgREST: PGRST202 (нет функции), PGRST205 (нет таблицы); Postgres:
 * 42883 (нет функции), 42P01 (нет таблицы), 42703 (нет столбца).
 */
export function isMissingSchema(error: { code?: string; message?: string } | null | undefined): boolean {
  if (!error) return false;
  return ["PGRST202", "PGRST205", "42883", "42P01", "42703"].includes(error.code ?? "");
}

export type Reservation =
  | { ok: true; tier: Tier; video_sec: number }
  | { ok: false; reason: "no_credits" | "legacy" | "error" };

/** Взять кредит под проект. Повтор по тому же проекту второй кредит не берёт. */
export async function reserveCredit(admin: Admin, projectId: string, tier: Tier): Promise<Reservation> {
  const { data, error } = await admin.rpc("reserve_credit", { p_project: projectId, p_tier: tier });
  if (error) {
    if (isMissingSchema(error)) return { ok: false, reason: "legacy" };
    if ((error.message ?? "").includes("no_credits")) return { ok: false, reason: "no_credits" };
    console.error("reserve_credit failed:", error.message);
    return { ok: false, reason: "error" };
  }
  const row = Array.isArray(data) ? data[0] : data;
  return { ok: true, tier: row?.tier ?? tier, video_sec: Number(row?.video_sec) || 0 };
}

/** Вернуть живой резерв проекта — для аварийных веток, где статус не меняется. */
export async function releaseCredit(admin: Admin, projectId: string): Promise<void> {
  const { error } = await admin.rpc("settle_credit", { p_project: projectId, p_outcome: "release" });
  if (error && !isMissingSchema(error)) console.error("credit release failed:", projectId, error.message);
}

/**
 * Включена ли система кредитов: миграция применена. Проверка дешёвая —
 * пустой запрос к таблице балансов.
 */
export async function creditsEnabled(admin: Admin): Promise<boolean> {
  const { error } = await admin.from("credit_balances").select("user_id", { head: true, count: "exact" }).limit(1);
  if (!error) return true;
  if (!isMissingSchema(error)) console.error("credits check failed:", error.message);
  return false;
}

/** Реквизиты для ручной оплаты. Пусто — просим написать на почту с номером заказа. */
export function paymentDetails(): string | null {
  const text = (process.env.PAYMENT_DETAILS ?? "").trim();
  return text || null;
}
