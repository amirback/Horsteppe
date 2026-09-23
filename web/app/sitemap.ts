import type { MetadataRoute } from "next";
import { LOCALES, LOCALE_META, SITE_URL } from "./lib/i18n";
import { PUBLIC_PATHS } from "./lib/seo";

/**
 * Карта сайта: все публичные страницы на всех языках, со связями между
 * переводами. Раньше /sitemap.xml отвечал 404, и поисковик узнавал о
 * справке и правовых страницах только если натыкался на ссылку в подвале.
 */
export default function sitemap(): MetadataRoute.Sitemap {
  return PUBLIC_PATHS.flatMap((path) =>
    LOCALES.map((lang) => ({
      url: `${SITE_URL}/${lang}${path}`,
      changeFrequency: path === "" ? ("weekly" as const) : ("monthly" as const),
      priority: path === "" ? 1 : path === "/pricing" ? 0.8 : 0.5,
      alternates: {
        languages: Object.fromEntries(
          LOCALES.map((l) => [LOCALE_META[l].htmlLang, `${SITE_URL}/${l}${path}`])
        ),
      },
    }))
  );
}
