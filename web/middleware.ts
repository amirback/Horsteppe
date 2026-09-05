import { NextResponse, type NextRequest } from "next/server";
import { LOCALES, isLang, pickLocale } from "./app/lib/i18n";

const COOKIE = "horsteppe-lang";

/**
 * Каждая страница живёт под своим языком: /en, /ru, /kk. Корень и любой
 * путь без префикса перенаправляются на язык, выбранный по cookie (то есть
 * по прошлому выбору пользователя), а если его нет — по заголовку браузера.
 */
export function middleware(request: NextRequest) {
  const { pathname, search, hash } = request.nextUrl;

  const hasLocale = LOCALES.some(
    (l) => pathname === `/${l}` || pathname.startsWith(`/${l}/`)
  );
  if (hasLocale) return NextResponse.next();

  const saved = request.cookies.get(COOKIE)?.value;
  const lang = isLang(saved) ? saved : pickLocale(request.headers.get("accept-language"));

  const url = request.nextUrl.clone();
  url.pathname = `/${lang}${pathname === "/" ? "" : pathname}`;
  url.search = search;
  url.hash = hash;
  return NextResponse.redirect(url);
}

export const config = {
  // Статика и служебные пути язык не выбирают
  matcher: ["/((?!_next|favicon|icon|apple-icon|opengraph|robots.txt|sitemap.xml|.*\\..*).*)"],
};
