import type { Lang } from "./i18n";

/**
 * Секунды на языке страницы: «31s», «31 с», «31 с».
 *
 * Раньше единица была латинской «s» на всех языках. Intl знает, как
 * пишется секунда в каждом из них, и ставить на это отдельные строки
 * перевода незачем.
 */
export function seconds(value: number, lang: Lang): string {
  const rounded = Math.round(value);
  try {
    return new Intl.NumberFormat(lang, { style: "unit", unit: "second", unitDisplay: "narrow" }).format(rounded);
  } catch {
    return `${rounded} s`;
  }
}

/**
 * Дата и время создания проекта в формате страны посетителя.
 *
 * Для английского берётся британский порядок «день месяц год»: он читается
 * однозначно во всём мире, в отличие от американского «месяц/день».
 */
export function when(iso: string, lang: Lang): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  try {
    return date.toLocaleString(lang === "en" ? "en-GB" : lang, {
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return date.toISOString().slice(0, 16).replace("T", " ");
  }
}
