import { createServerClient, type CookieOptions } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";
import { LOCALES, isLang, pickLocale } from "./app/lib/i18n";
import { isBackendReady } from "./lib/supabase/env";

const COOKIE = "horsteppe-lang";

type CookieToSet = { name: string; value: string; options?: CookieOptions };

/**
 * Один middleware решает три задачи по порядку:
 *
 *   1. `/api/*` — язык не выбирается, только обновление сессии и защита;
 *   2. страница без языкового префикса — редирект на нужный язык;
 *   3. остальное — обновление сессии и защита `/<язык>/projects`.
 *
 * Если backend ещё не подключён, вся работа с сессией пропускается: лендинг
 * обязан открываться и без базы.
 */
export async function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;

  if (pathname.startsWith("/api/")) {
    return handleApi(request);
  }

  const hasLocale = LOCALES.some((l) => pathname === `/${l}` || pathname.startsWith(`/${l}/`));
  if (!hasLocale) {
    const saved = request.cookies.get(COOKIE)?.value;
    const lang = isLang(saved) ? saved : pickLocale(request.headers.get("accept-language"));
    const url = request.nextUrl.clone();
    url.pathname = `/${lang}${pathname === "/" ? "" : pathname}`;
    url.search = search;
    return NextResponse.redirect(url);
  }

  return handlePage(request);
}

/** Возвращает пару: клиент Supabase и ответ, в который он пишет cookie сессии. */
function withSession(request: NextRequest) {
  let response = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet: CookieToSet[]) {
          cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
          response = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options)
          );
        },
      },
    }
  );

  return { supabase, getResponse: () => response };
}

async function handleApi(request: NextRequest) {
  const protectedApi = request.nextUrl.pathname.startsWith("/api/projects");

  if (!isBackendReady()) {
    // Честный отказ вместо падения: фронтенд покажет понятное сообщение.
    return protectedApi
      ? NextResponse.json({ error: "backend_not_configured" }, { status: 503 })
      : NextResponse.next();
  }

  const { supabase, getResponse } = withSession(request);
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user && protectedApi) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }
  return getResponse();
}

async function handlePage(request: NextRequest) {
  if (!isBackendReady()) return NextResponse.next();

  const { supabase, getResponse } = withSession(request);
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const segments = request.nextUrl.pathname.split("/").filter(Boolean);
  const lang = segments[0];
  const isProjects = segments[1] === "projects";

  if (!user && isProjects && isLang(lang)) {
    const url = request.nextUrl.clone();
    url.pathname = `/${lang}/login`;
    url.searchParams.set("next", request.nextUrl.pathname);
    return NextResponse.redirect(url);
  }

  return getResponse();
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|icon.svg|robots.txt|sitemap.xml|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)",
  ],
};
