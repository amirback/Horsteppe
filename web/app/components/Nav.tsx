"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { content } from "../lib/content";
import { LOCALES, LOCALE_META, type Lang } from "../lib/i18n";
import { Logo } from "./ui";
import { Magnetic, motion } from "./motion";
import { UserMenu } from "./UserMenu";

export function rememberLang(lang: Lang) {
  try {
    document.cookie = `horsteppe-lang=${lang}; path=/; max-age=31536000; samesite=lax`;
  } catch {
    /* cookie отключены — язык просто не запомнится */
  }
}

/**
 * Навигация. На обложке лежит поверх зелёного фона, на остальных страницах —
 * на бумажном. Пунктов всего два: продукт и тарифы. Больше в SaaS не нужно,
 * а лишние ссылки уводят от единственного действия — создать видео.
 */
export function Nav({
  lang,
  overlay = false,
  email = null,
}: {
  lang: Lang;
  overlay?: boolean;
  /** Почта вошедшего пользователя. null — показываем кнопку входа. */
  email?: string | null;
}) {
  const t = content[lang];
  const [open, setOpen] = useState(false);
  const [solid, setSolid] = useState(!overlay);

  useEffect(() => {
    if (!overlay) return;
    const onScroll = () => setSolid(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [overlay]);

  const links = [
    { href: `/${lang}#how`, label: t.nav.product },
    { href: `/${lang}/pricing`, label: t.nav.pricing },
  ];

  return (
    <header
      className={[
        "fixed inset-x-0 top-0 z-50 transition-colors duration-300",
        solid ? "border-b border-ink/10 bg-paper/85 backdrop-blur-xl" : "border-b border-transparent",
      ].join(" ")}
    >
      <div className="container-x flex h-[68px] items-center justify-between gap-4 md:h-20">
        <Link href={`/${lang}`} aria-label="Horsteppe" className="shrink-0">
          <Logo animate={overlay} />
        </Link>

        <nav className="hidden items-center gap-8 md:flex">
          {links.map((l) => (
            <Link key={l.label} href={l.href} className="nav-link text-ink transition-opacity hover:opacity-60">
              {l.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          {email ? null : (
            <Link
              href={`/${lang}/login`}
              className="nav-link hidden text-ink-soft/75 transition hover:text-ink sm:block"
            >
              {t.nav.signIn}
            </Link>
          )}
          <Magnetic strength={0.14} className="hidden sm:inline-block">
            <Link
              href={`/${lang}#top`}
              className="nav-link inline-flex items-center rounded-full bg-ink px-5 py-2.5 text-cream transition hover:bg-forest"
            >
              {t.nav.cta}
            </Link>
          </Magnetic>

          {email ? <UserMenu lang={lang} email={email} /> : null}

          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-label="Menu"
            aria-expanded={open}
            className="flex h-10 w-10 items-center justify-center rounded-full border-[1.5px] border-ink/30 text-ink transition hover:border-ink md:hidden"
          >
            <svg viewBox="0 0 20 20" fill="none" className="h-4 w-4">
              <path
                d={open ? "M5 5l10 10M15 5L5 15" : "M3 6h14M3 10h14M3 14h14"}
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
              />
            </svg>
          </button>
        </div>
      </div>

      {open ? (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          className="overflow-hidden border-t border-ink/10 bg-paper/95 backdrop-blur-xl md:hidden"
        >
          <div className="container-x flex flex-col gap-1 py-4">
            {links.map((l) => (
              <Link
                key={l.label}
                href={l.href}
                onClick={() => setOpen(false)}
                className="nav-link rounded-xl px-3 py-3 text-ink transition hover:bg-ink/5"
              >
                {l.label}
              </Link>
            ))}
            {email ? (
              <span className="nav-link truncate px-3 py-3 text-ink-soft/60">{email}</span>
            ) : (
              <Link
                href={`/${lang}/login`}
                onClick={() => setOpen(false)}
                className="nav-link rounded-xl px-3 py-3 text-ink-soft/80 transition hover:bg-ink/5"
              >
                {t.nav.signIn}
              </Link>
            )}
            <Link
              href={`/${lang}#top`}
              onClick={() => setOpen(false)}
              className="nav-link mt-2 rounded-full bg-ink px-5 py-3 text-center text-cream"
            >
              {t.nav.cta}
            </Link>
            <div className="mt-3 flex gap-2 border-t border-ink/10 pt-4">
              {LOCALES.map((l) => (
                <a
                  key={l}
                  href={`/${l}`}
                  onClick={() => rememberLang(l)}
                  className={[
                    "nav-link rounded-full px-4 py-2 transition",
                    l === lang ? "bg-ink text-cream" : "border border-ink/20 text-ink-soft/70",
                  ].join(" ")}
                >
                  {LOCALE_META[l].label}
                </a>
              ))}
            </div>
          </div>
        </motion.div>
      ) : null}
    </header>
  );
}
