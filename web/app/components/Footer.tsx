"use client";

import { content, CONTACT_EMAIL } from "../lib/content";
import { LOCALES, LOCALE_META, type Lang } from "../lib/i18n";
import { rememberLang } from "./Nav";

export function Footer({ lang }: { lang: Lang }) {
  const t = content[lang];
  return (
    <footer className="border-t border-ink/10 py-10">
      <div className="container-x flex flex-col gap-7 sm:flex-row sm:items-start sm:justify-between">
        <p className="max-w-xs text-[13.5px] leading-relaxed text-ink-soft/75">{t.footer.tagline}</p>

        <div className="flex flex-col gap-6 sm:flex-row sm:gap-12">
          <div>
            <div className="nav-link text-ink-soft/50">{t.footer.contact}</div>
            <a
              href={`mailto:${CONTACT_EMAIL}`}
              className="mt-2 inline-block text-[14px] text-ink underline decoration-ink/25 underline-offset-4 transition hover:decoration-ink"
            >
              {CONTACT_EMAIL}
            </a>
          </div>

          <div>
            <div className="nav-link text-ink-soft/50">{t.footer.lang}</div>
            <div className="mt-2 inline-flex rounded-full border border-ink/15 p-0.5">
              {LOCALES.map((l) => (
                <a
                  key={l}
                  href={`/${l}`}
                  hrefLang={LOCALE_META[l].htmlLang}
                  onClick={() => rememberLang(l)}
                  aria-current={lang === l ? "true" : undefined}
                  title={LOCALE_META[l].native}
                  className={[
                    "nav-link rounded-full px-3 py-1.5 transition",
                    lang === l ? "bg-ink text-cream" : "text-ink-soft/60 hover:text-ink",
                  ].join(" ")}
                >
                  {LOCALE_META[l].label}
                </a>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="container-x mt-8 flex flex-wrap items-center justify-between gap-3 border-t border-ink/10 pt-5 text-[12px] text-ink-soft/55">
        <span>© {new Date().getFullYear()} Horsteppe. {t.footer.rights}</span>
        <span>{t.footer.orda}</span>
      </div>
    </footer>
  );
}
