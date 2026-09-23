import type { Lang } from "./i18n";

/**
 * Подписи ссылок на справку и правовые документы.
 *
 * Отдельным модулем, а не частью legal-content.ts, ради веса страницы.
 * Подвал — клиентский компонент, и всё, что он импортирует, едет в браузер.
 * Раньше он брал подписи из общего словаря документов — и вместе с четырьмя
 * словами в браузер уезжали 50 КБ полных правовых текстов на всех трёх
 * языках, на каждой странице сайта.
 */
export type LegalDoc = "privacy" | "terms" | "cookies" | "help";

export const legalNav: Record<Lang, Record<LegalDoc, string>> = {
  en: { privacy: "Privacy", terms: "Terms", cookies: "Cookies", help: "Help center" },
  ru: { privacy: "Конфиденциальность", terms: "Условия", cookies: "Cookie", help: "Справка" },
  kk: { privacy: "Құпиялылық", terms: "Шарттар", cookies: "Cookie", help: "Анықтама" },
};
