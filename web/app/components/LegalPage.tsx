"use client";

import Link from "next/link";
import { CONTACT_EMAIL } from "../lib/content";
import { legal, type LegalDoc } from "../lib/legal-content";
import type { Lang } from "../lib/i18n";
import { Nav } from "./Nav";
import { Ambience } from "./Ambience";
import { Footer } from "./Footer";
import { Reveal } from "./motion";

const ORDER: LegalDoc[] = ["help", "privacy", "terms", "cookies"];

/**
 * Общий шаблон для справки и юридических документов.
 *
 * Все четыре страницы устроены одинаково и переключаются между собой, поэтому
 * в подвале главной хватает одного ряда ссылок — сами тексты никакого места
 * на сайте не занимают.
 */
export function LegalPage({ lang, doc, email }: { lang: Lang; doc: LegalDoc; email: string | null }) {
  const l = legal[lang];
  const d = l.docs[doc];

  return (
    <>
      <Ambience />
      <Nav lang={lang} email={email} />

      <main className="container-x pb-16 pt-28 md:pb-24 md:pt-36">
        <div className="grid gap-10 lg:grid-cols-[210px_1fr] lg:gap-14">
          {/* Переключатель документов: сбоку на широком экране, лентой на узком */}
          {/* Лента без выноса за края: отрицательные поля делали блок шире
              экрана и вызывали горизонтальную прокрутку на узких телефонах. */}
          <nav className="min-w-0 overflow-x-auto lg:overflow-visible">
            <ul className="flex gap-2 lg:sticky lg:top-28 lg:flex-col lg:gap-1">
              {ORDER.map((key) => {
                const active = key === doc;
                return (
                  <li key={key} className="shrink-0">
                    <Link
                      href={`/${lang}/${key}`}
                      aria-current={active ? "page" : undefined}
                      className={[
                        // На широком экране перенос разрешён: «Конфиденциальность»
                        // не помещалась в боковую колонку и обрезалась.
                        "nav-link block whitespace-nowrap rounded-full px-4 py-2 transition lg:whitespace-normal lg:rounded-xl lg:px-3 lg:leading-snug",
                        active
                          ? "bg-ink text-cream"
                          : "border border-ink/15 text-ink-soft/70 hover:text-ink lg:border-0 lg:hover:bg-ink/5",
                      ].join(" ")}
                    >
                      {l.nav[key]}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </nav>

          <article className="min-w-0 max-w-2xl">
            <Reveal>
              {/* Размер зависит от ширины экрана: «Политика конфиденциальности» —
                  это одно длинное слово, переносить его негде, и на 320 пикселях
                  фиксированные 30px вылезали за край страницы. */}
              <h1 className="font-display text-balance font-bold leading-[1.12] tracking-[-0.025em] text-ink [font-size:clamp(21px,6.4vw,40px)] [overflow-wrap:anywhere]">
                {d.title}
              </h1>
              <p className="nav-link mt-3 text-ink-soft/50">
                {l.updatedLabel}: {d.updated}
              </p>
              <p className="mt-6 text-[15.5px] leading-relaxed text-ink-soft/85 md:text-[16.5px]">{d.intro}</p>
            </Reveal>

            <div className="mt-10 space-y-9">
              {d.sections.map((s) => (
                <Reveal key={s.h}>
                  <section>
                    <h2 className="font-display text-[17.5px] font-bold tracking-[-0.01em] text-ink md:text-[19px]">
                      {s.h}
                    </h2>
                    <div className="mt-3 space-y-3">
                      {s.p.map((text) => (
                        <p key={text} className="text-[14.5px] leading-relaxed text-ink-soft/85 md:text-[15.5px]">
                          {text}
                        </p>
                      ))}
                    </div>
                  </section>
                </Reveal>
              ))}
            </div>

            <Reveal>
              <p className="mt-12 border-t border-ink/10 pt-6 text-[14px] text-ink-soft/75">
                {l.contactNote}{" "}
                <a
                  href={`mailto:${CONTACT_EMAIL}`}
                  className="text-ink underline decoration-ink/25 underline-offset-4 transition hover:decoration-ink"
                >
                  {CONTACT_EMAIL}
                </a>
              </p>
            </Reveal>
          </article>
        </div>
      </main>

      <Footer lang={lang} />
    </>
  );
}
