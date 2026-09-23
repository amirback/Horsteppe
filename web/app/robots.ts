import type { MetadataRoute } from "next";
import { SITE_URL } from "./lib/i18n";

/**
 * Правила для поисковых роботов.
 *
 * Раньше /robots.txt отвечал 404, и роботы ходили везде, включая вход и
 * личные страницы проектов. API закрыт целиком: там нечего индексировать,
 * а каждый визит робота — это вызов функции и запрос к базе.
 */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/api/", "/*/login", "/*/projects"],
      },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
    host: SITE_URL,
  };
}
