import type { Metadata } from "next";
import { LOCALES, LOCALE_META, SITE_URL, type Lang } from "./i18n";

/** Заголовок и описание сайта для поиска и соцсетей — на каждом языке. */
export const SEO: Record<Lang, { title: string; description: string }> = {
  en: {
    title: "Horsteppe — Orchestrating the Steppe",
    description:
      "The pipeline that harnesses AI to create your video masterpiece: it writes the script, plans the scenes, generates the visuals, records the voice, edits and delivers a finished MP4.",
  },
  ru: {
    title: "Horsteppe — оркестровка степи",
    description:
      "Конвейер, который направляет ИИ на создание вашего видеошедевра: пишет сценарий, планирует сцены, создаёт визуал, озвучивает, монтирует и отдаёт готовый MP4.",
  },
  kk: {
    title: "Horsteppe — дала оркестрі",
    description:
      "Жасанды интеллектті бейне-шедевріңізді жасауға жұмылдыратын конвейер: сценарий жазады, сценаларды жоспарлайды, кадр жасайды, дауыстайды, монтаждайды және дайын MP4 береді.",
  },
};

/** Публичные страницы, которые стоит показывать поиску. Путь — после языка. */
export const PUBLIC_PATHS = ["", "/pricing", "/help", "/privacy", "/terms", "/cookies"] as const;

/**
 * Метаданные конкретной страницы.
 *
 * Раньше их задавал только общий макет, и у всех страниц был один
 * канонический адрес — главная своего языка. Тарифы, справка и правовые
 * тексты сообщали поисковику: «я дубль главной, меня не индексируй».
 * Теперь у каждой страницы свой адрес, свои связи между языками и своя
 * ссылка для соцсетей.
 *
 * `index: false` — для страниц, которым в поиске делать нечего: вход и
 * личные проекты. Ссылка на чужой проект из поиска бесполезна, а вход без
 * контекста выглядит как мусор в выдаче.
 */
export function pageMetadata(
  lang: Lang,
  path: string,
  { title, index = true }: { title?: string; index?: boolean } = {}
): Metadata {
  const url = `${SITE_URL}/${lang}${path}`;
  const languages = Object.fromEntries(
    LOCALES.map((l) => [LOCALE_META[l].htmlLang, `${SITE_URL}/${l}${path}`])
  );
  const seo = SEO[lang];
  const shareTitle = title ? `${title} · Horsteppe` : seo.title;

  return {
    ...(title ? { title } : {}),
    description: seo.description,
    alternates: {
      canonical: url,
      languages: { ...languages, "x-default": `${SITE_URL}/en${path}` },
    },
    openGraph: {
      type: "website",
      url,
      siteName: "Horsteppe",
      title: shareTitle,
      description: seo.description,
      locale: LOCALE_META[lang].ogLocale,
      images: [{ url: "/og.png", width: 1200, height: 630, alt: "Horsteppe" }],
      alternateLocale: LOCALES.filter((l) => l !== lang).map((l) => LOCALE_META[l].ogLocale),
    },
    twitter: {
      card: "summary_large_image",
      title: shareTitle,
      description: seo.description,
      images: ["/og.png"],
    },
    robots: index ? { index: true, follow: true } : { index: false, follow: false },
  };
}
