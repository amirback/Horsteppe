"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { content } from "../lib/content";
import { LOCALES, LOCALE_META, type Lang } from "../lib/i18n";
import { Mesh } from "./Mesh";
import { Logo, Pill, SearchIcon } from "./ui";
import { Magnetic, ScrollProgress, motion } from "./motion";
import {
  Blog,
  Budget,
  Cta,
  Demo,
  Faq,
  Features,
  Footer,
  Hero,
  How,
  Pricing,
  Problem,
  Roadmap,
  Team,
} from "./sections";

/** Запоминаем выбор языка, чтобы middleware не переспрашивал браузер. */
export function rememberLang(lang: Lang) {
  try {
    document.cookie = `horsteppe-lang=${lang}; path=/; max-age=31536000; samesite=lax`;
  } catch {
    /* cookie отключены — язык просто не запомнится */
  }
}

export default function Landing({ lang }: { lang: Lang }) {
  const [pastHero, setPastHero] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const onScroll = () => setPastHero(window.scrollY > window.innerHeight - 110);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    if (searchOpen) inputRef.current?.focus();
  }, [searchOpen]);

  const t = content[lang];

  const links = [
    { href: "#top", label: t.nav.home },
    { href: "#how", label: t.nav.product },
    { href: "#team", label: t.nav.team },
    { href: "#pricing", label: t.nav.pricing },
    { href: "#blog", label: t.nav.blog },
  ];

  const index = useMemo(
    () => [
      { href: "#how", title: t.how.title, body: t.how.steps.map((s) => `${s.title} ${s.text}`).join(" ") },
      { href: "#engine", title: t.budget.title, body: t.budget.sub },
      { href: "#features", title: t.features.title, body: t.features.items.map((f) => `${f.title} ${f.text}`).join(" ") },
      { href: "#roadmap", title: t.roadmap.title, body: t.roadmap.columns.flatMap((c) => c.items).join(" ") },
      { href: "#demo", title: t.demo.title, body: t.demo.sub },
      { href: "#team", title: t.team.title, body: t.team.roles.map((r) => `${r.role} ${r.text}`).join(" ") },
      { href: "#pricing", title: t.pricing.title, body: t.pricing.tiers.map((x) => `${x.name} ${x.items.join(" ")}`).join(" ") },
      { href: "#blog", title: t.blog.title, body: t.blog.posts.map((p) => `${p.title} ${p.text}`).join(" ") },
      { href: "#faq", title: t.faq.title, body: t.faq.items.map((i) => `${i.q} ${i.a}`).join(" ") },
    ],
    [t]
  );

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (q.length < 2) return [];
    return index.filter((s) => `${s.title} ${s.body}`.toLowerCase().includes(q)).slice(0, 5);
  }, [query, index]);

  const closeSearch = () => {
    setSearchOpen(false);
    setQuery("");
  };

  const navInner = (
    <div className="container-x flex h-24 items-center justify-between gap-6 md:h-28">
      <a href="#top" aria-label="Horsteppe" className="shrink-0">
        <Logo />
      </a>

      <div className="hidden items-center gap-9 lg:flex xl:gap-12">
        {links.map((l) => (
          <a
            key={l.label}
            href={l.href}
            className="nav-link relative text-ink transition-opacity hover:opacity-60"
          >
            {l.label}
          </a>
        ))}
      </div>

      <div className="flex items-center gap-2">
        <div className="relative">
          {searchOpen ? (
            <div className="flex items-center gap-2 rounded-full border-[1.5px] border-ink bg-paper/90 px-4 py-2.5 backdrop-blur">
              <SearchIcon className="h-4 w-4 shrink-0 text-ink" />
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Escape") closeSearch();
                  if (e.key === "Enter" && results[0]) {
                    window.location.hash = results[0].href;
                    closeSearch();
                  }
                }}
                placeholder={t.searchUi.placeholder}
                className="w-40 bg-transparent text-[13px] text-ink outline-none placeholder:text-ink-soft/45 sm:w-56"
              />
              <button
                type="button"
                onClick={closeSearch}
                aria-label={t.searchUi.close}
                className="text-ink-soft/60 transition hover:text-ink"
              >
                <svg viewBox="0 0 20 20" fill="none" className="h-4 w-4">
                  <path d="M5 5l10 10M15 5L5 15" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
                </svg>
              </button>
            </div>
          ) : (
            <span className="hidden sm:inline-block">
              <Magnetic strength={0.18}>
                <Pill
                  as="button"
                  onClick={() => setSearchOpen(true)}
                  className="w-[200px] justify-start gap-3 pl-6 text-ink hover:bg-ink hover:text-cream"
                >
                  <SearchIcon className="h-4 w-4" />
                  {t.nav.search}
                </Pill>
              </Magnetic>
            </span>
          )}

          {searchOpen && query.trim().length >= 2 ? (
            <motion.div
              initial={{ opacity: 0, y: -6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25 }}
              className="absolute right-0 top-full z-50 mt-2 w-[min(22rem,calc(100vw-3rem))] overflow-hidden rounded-2xl border border-ink/15 bg-paper shadow-xl"
            >
              {results.length ? (
                results.map((r) => (
                  <a
                    key={r.href}
                    href={r.href}
                    onClick={closeSearch}
                    className="block border-b border-ink/8 px-4 py-3 text-[13.5px] leading-snug text-ink-soft transition last:border-0 hover:bg-ink/5 hover:text-ink"
                  >
                    {r.title}
                  </a>
                ))
              ) : (
                <div className="px-4 py-3 text-[13.5px] text-ink-soft/60">{t.searchUi.empty}</div>
              )}
            </motion.div>
          ) : null}
        </div>

        <button
          type="button"
          onClick={() => setMenuOpen((v) => !v)}
          aria-label="Menu"
          aria-expanded={menuOpen}
          className="flex h-10 w-10 items-center justify-center rounded-full border-[1.5px] border-ink text-ink lg:hidden"
        >
          <svg viewBox="0 0 20 20" fill="none" className="h-4.5 w-4.5">
            <path
              d={menuOpen ? "M5 5l10 10M15 5L5 15" : "M3 6h14M3 10h14M3 14h14"}
              stroke="currentColor"
              strokeWidth="1.7"
              strokeLinecap="round"
            />
          </svg>
        </button>
      </div>
    </div>
  );

  const mobileMenu = (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={{ opacity: 0, height: 0 }}
      className="container-x overflow-hidden pb-5 lg:hidden"
    >
      <div className="flex flex-col gap-1 border-t border-ink/15 pt-4">
        {links.map((l) => (
          <a
            key={l.label}
            href={l.href}
            onClick={() => setMenuOpen(false)}
            className="nav-link rounded-full px-3 py-3 text-ink transition hover:bg-ink/8"
          >
            {l.label}
          </a>
        ))}
        <div className="mt-3 flex gap-2 border-t border-ink/15 pt-4">
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
  );

  return (
    <>
      <ScrollProgress />

      {/* Экран-обложка: навигация лежит поверх зелёного фона, как в макете */}
      <header id="top" className="relative isolate">
        <Mesh />
        <nav className="relative z-20">
          {navInner}
          {menuOpen ? mobileMenu : null}
        </nav>
        <div className="relative z-10">
          <Hero t={t} lang={lang} />
        </div>
      </header>

      {/* Липкая навигация появляется только после обложки, чтобы не спорить с макетом */}
      <motion.nav
        initial={false}
        animate={{ y: pastHero ? 0 : "-100%" }}
        transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
        className="fixed inset-x-0 top-0 z-50 border-b border-ink/10 bg-paper/90 backdrop-blur-xl"
      >
        {navInner}
        {menuOpen && pastHero ? mobileMenu : null}
      </motion.nav>

      <main>
        <Problem t={t} />
        <How t={t} />
        <Budget t={t} />
        <Features t={t} />
        <Roadmap t={t} />
        <Demo t={t} />
        <Team t={t} />
        <Pricing t={t} />
        <Blog t={t} />
        <Faq t={t} />
        <Cta t={t} />
      </main>

      <Footer t={t} lang={lang} />
    </>
  );
}
