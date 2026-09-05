"use client";

import { useEffect, useState } from "react";
import { content, type Lang } from "../lib/content";
import { Logo } from "./ui";
import {
  Budget,
  Cta,
  Demo,
  Faq,
  Features,
  Footer,
  Hero,
  How,
  Problem,
  Roadmap,
  mailtoHref,
} from "./sections";

const LANG_KEY = "horsteppe-lang";

export default function Landing() {
  const [lang, setLang] = useState<Lang>("ru");
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(LANG_KEY);
      if (saved === "ru" || saved === "en") setLang(saved);
    } catch {
      /* приватный режим — просто оставляем язык по умолчанию */
    }
  }, []);

  useEffect(() => {
    document.documentElement.lang = lang;
    try {
      window.localStorage.setItem(LANG_KEY, lang);
    } catch {
      /* не критично */
    }
  }, [lang]);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const t = content[lang];

  const links = [
    { href: "#how", label: t.nav.how },
    { href: "#engine", label: t.nav.engine },
    { href: "#features", label: t.nav.features },
    { href: "#faq", label: t.nav.faq },
  ];

  return (
    <>
      <nav
        className={[
          "fixed inset-x-0 top-0 z-50 transition-colors duration-300",
          scrolled || menuOpen
            ? "border-b border-line-soft bg-ink/85 backdrop-blur-xl"
            : "border-b border-transparent",
        ].join(" ")}
      >
        <div className="container-x flex h-16 items-center justify-between gap-4">
          <a href="#top" className="shrink-0" aria-label="Horsteppe">
            <Logo />
          </a>

          <div className="hidden items-center gap-7 lg:flex">
            {links.map((l) => (
              <a
                key={l.href}
                href={l.href}
                className="text-[14px] text-muted transition hover:text-cream"
              >
                {l.label}
              </a>
            ))}
          </div>

          <div className="flex items-center gap-2.5">
            <div className="flex items-center rounded-lg border border-line bg-surface/60 p-0.5">
              {(["ru", "en"] as const).map((l) => (
                <button
                  key={l}
                  type="button"
                  onClick={() => setLang(l)}
                  aria-pressed={lang === l}
                  className={[
                    "rounded-[6px] px-2.5 py-1 text-[12px] font-medium uppercase transition",
                    lang === l
                      ? "bg-surface-2 text-cream"
                      : "text-muted-2 hover:text-muted",
                  ].join(" ")}
                >
                  {l}
                </button>
              ))}
            </div>

            <a
              href={mailtoHref(t)}
              className="hidden rounded-lg bg-amber px-4 py-2 text-[13.5px] font-semibold text-[#1a1206] transition hover:bg-amber-soft sm:inline-flex"
            >
              {t.nav.cta}
            </a>

            <button
              type="button"
              onClick={() => setMenuOpen((v) => !v)}
              aria-label="Menu"
              aria-expanded={menuOpen}
              className="flex h-9 w-9 items-center justify-center rounded-lg border border-line text-muted lg:hidden"
            >
              <svg viewBox="0 0 20 20" fill="none" className="h-4.5 w-4.5">
                <path
                  d={menuOpen ? "M5 5l10 10M15 5L5 15" : "M3 6h14M3 10h14M3 14h14"}
                  stroke="currentColor"
                  strokeWidth="1.6"
                  strokeLinecap="round"
                />
              </svg>
            </button>
          </div>
        </div>

        {menuOpen ? (
          <div className="container-x pb-5 lg:hidden">
            <div className="flex flex-col gap-1 border-t border-line-soft pt-4">
              {links.map((l) => (
                <a
                  key={l.href}
                  href={l.href}
                  onClick={() => setMenuOpen(false)}
                  className="rounded-lg px-2 py-2.5 text-[15px] text-muted transition hover:bg-surface/60 hover:text-cream"
                >
                  {l.label}
                </a>
              ))}
              <a
                href={mailtoHref(t)}
                onClick={() => setMenuOpen(false)}
                className="mt-2 rounded-lg bg-amber px-4 py-3 text-center text-[15px] font-semibold text-[#1a1206] sm:hidden"
              >
                {t.nav.cta}
              </a>
            </div>
          </div>
        ) : null}
      </nav>

      <main id="top">
        <Hero t={t} />
        <Problem t={t} />
        <How t={t} />
        <Budget t={t} />
        <Features t={t} />
        <Roadmap t={t} />
        <Demo t={t} />
        <Faq t={t} />
        <Cta t={t} />
      </main>

      <Footer t={t} />
    </>
  );
}
