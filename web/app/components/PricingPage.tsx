"use client";

import Link from "next/link";
import { content } from "../lib/content";
import type { Lang } from "../lib/i18n";
import { Nav } from "./Nav";
import { Ambience } from "./Ambience";
import { Footer } from "./Footer";
import { CheckIcon } from "./ui";
import { Reveal, Stagger, StaggerItem } from "./motion";

export function PricingPage({ lang }: { lang: Lang }) {
  const t = content[lang];
  const p = t.pricing;

  return (
    <>
      <Ambience />
      <Nav lang={lang} />

      <main className="container-x pb-16 pt-28 md:pb-24 md:pt-36">
        <Reveal>
          <div className="nav-link text-ink-soft/55">{p.kicker}</div>
          <h1 className="font-display mt-3 max-w-2xl text-balance text-[30px] font-bold leading-[1.1] tracking-[-0.025em] text-ink md:text-[44px]">
            {p.title}
          </h1>
          <p className="mt-4 max-w-xl text-[15px] leading-relaxed text-ink-soft/85 md:text-[16px]">{p.sub}</p>
        </Reveal>

        <Stagger className="mt-10 grid gap-4 md:mt-14 md:grid-cols-3 md:gap-5" gap={0.1}>
          {p.tiers.map((tier) => (
            <StaggerItem
              key={tier.name}
              className={[
                "flex flex-col rounded-3xl p-6 md:p-7",
                tier.highlight ? "bg-forest text-cream" : "border border-ink/12 bg-white/45",
              ].join(" ")}
            >
              <h2 className={`font-display text-[17px] font-bold ${tier.highlight ? "text-cream" : "text-ink"}`}>
                {tier.name}
              </h2>
              <div
                className={`font-display mt-3 text-[26px] font-bold tracking-[-0.02em] ${tier.highlight ? "text-lime" : "text-ink"}`}
              >
                {tier.price}
              </div>

              <ul className="mt-5 flex-1 space-y-2.5">
                {tier.items.map((item) => (
                  <li key={item} className="flex items-start gap-2.5">
                    <CheckIcon className={`mt-0.5 h-4 w-4 shrink-0 ${tier.highlight ? "text-lime" : "text-sage"}`} />
                    <span className={`text-[13.5px] leading-snug ${tier.highlight ? "text-cream/85" : "text-ink-soft/85"}`}>
                      {item}
                    </span>
                  </li>
                ))}
              </ul>

              {tier.highlight ? (
                <Link
                  href={`/${lang}#top`}
                  className="nav-link mt-6 inline-flex items-center justify-center rounded-full bg-cream px-6 py-3 text-forest transition hover:bg-lime"
                >
                  {p.cta}
                </Link>
              ) : null}
            </StaggerItem>
          ))}
        </Stagger>

        <Reveal>
          <p className="mt-8 max-w-2xl text-[12.5px] leading-relaxed text-ink-soft/60">{p.note}</p>
        </Reveal>
      </main>

      <Footer lang={lang} />
    </>
  );
}
