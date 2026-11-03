/**
 * Оценка готового ролика: правила, общие для API и страницы проекта.
 *
 * ТЗ V1, Phase 4: «Хороший результат» или «Нужно улучшить», а при втором —
 * причина и необязательный комментарий, привязанные к конкретной генерации,
 * модели и настройкам. Это сбор данных для будущего выбора моделей, а не
 * обучение — так оценка и называется в интерфейсе.
 *
 * Списки совпадают с проверкой таблицы project_feedback в миграции 0006;
 * расхождение ловит scripts/check-feedback.mjs.
 */

export const FEEDBACK_RATINGS = ["good", "needs_improvement"] as const;
export const FEEDBACK_REASONS = [
  "off_prompt", "visuals", "motion", "sound", "text", "length", "other",
] as const;
export const MAX_COMMENT = 1000;

export type Rating = (typeof FEEDBACK_RATINGS)[number];
export type Reason = (typeof FEEDBACK_REASONS)[number];
export type Feedback = { rating: Rating; reasons: Reason[]; comment: string | null };

/**
 * Проверить то, что прислал браузер. null — прислано не то.
 *
 * «Нужно улучшить» без единой причины не принимается: такая оценка ничего
 * не говорит о том, что чинить. У хорошей оценки причин нет по смыслу.
 */
export function parseFeedback(raw: unknown): Feedback | null {
  if (!raw || typeof raw !== "object") return null;
  const body = raw as { rating?: unknown; reasons?: unknown; comment?: unknown };
  if (!FEEDBACK_RATINGS.includes(body.rating as Rating)) return null;
  const rating = body.rating as Rating;

  const given = body.reasons ?? [];
  if (!Array.isArray(given) || given.length > FEEDBACK_REASONS.length) return null;
  if (!given.every((r) => FEEDBACK_REASONS.includes(r as Reason))) return null;
  const reasons = rating === "good" ? [] : [...new Set(given as Reason[])];
  if (rating === "needs_improvement" && reasons.length === 0) return null;

  if (body.comment !== undefined && body.comment !== null && typeof body.comment !== "string") return null;
  const comment = typeof body.comment === "string" ? body.comment.trim() : "";
  if (comment.length > MAX_COMMENT) return null;

  return { rating, reasons, comment: comment || null };
}

type ShotRow = { provider: string | null; model: string | null; generation_mode: string | null };
export type VideoSource = { provider: string; model: string; shots: number };

/**
 * Кто на самом деле сделал настоящие клипы ролика.
 *
 * ТЗ запрещает тихо менять провайдера. В базе честно записано, какой
 * провайдер сделал каждый кадр, — эта сводка показывает это человеку и
 * сохраняется вместе с оценкой.
 */
export function summarizeSources(shots: ShotRow[]): VideoSource[] {
  const counts = new Map<string, VideoSource>();
  for (const shot of shots) {
    if (shot.generation_mode !== "real_video" || !shot.provider) continue;
    const key = `${shot.provider}\u0000${shot.model ?? ""}`;
    const entry = counts.get(key) ?? { provider: shot.provider, model: shot.model ?? "", shots: 0 };
    entry.shots += 1;
    counts.set(key, entry);
  }
  return [...counts.values()].sort((a, b) => b.shots - a.shots);
}

/** Человеческое имя модели: «kling-video/v2.5-turbo/pro/image-to-video» → «Kling 2.5 Turbo Pro». */
export function modelLabel(model: string): string {
  const known: Record<string, string> = {
    "kling-video/v2.5-turbo/pro/image-to-video": "Kling 2.5 Turbo Pro",
    "kling-video/v2.5-turbo/standard/image-to-video": "Kling 2.5 Turbo",
    "minimax/hailuo-2.3/standard/image-to-video": "Hailuo 2.3",
  };
  return known[model] ?? model;
}

export function providerLabel(provider: string): string {
  const known: Record<string, string> = { higgsfield: "Higgsfield", fal: "fal.ai", replicate: "Replicate" };
  return known[provider] ?? provider;
}

/** Таблицы ещё нет — миграция 0006 не применена. Тогда оценка честно недоступна. */
export function isMissingTable(error: { code?: string | null; message?: string | null } | null): boolean {
  if (!error) return false;
  if (error.code === "PGRST205" || error.code === "42P01") return true;
  const text = (error.message ?? "").toLowerCase();
  return text.includes("project_feedback") && (text.includes("schema cache") || text.includes("does not exist"));
}
