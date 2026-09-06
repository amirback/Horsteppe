"use client";

import { useState } from "react";
import type { Dict } from "../lib/content";
import { CONTACT_EMAIL } from "../lib/content";
import { Words } from "./motion";
import { Generator } from "./Generator";
import {
  ArrowIcon,
  CheckIcon,
  FEATURE_ICONS,
  FeatureIcon,
  H2,
  Kicker,
  Lead,
  Pill,
  PlayIcon,
  Section,
} from "./ui";
import { GrowBar, Magnetic, Marquee, Reveal, Stagger, StaggerItem, motion } from "./motion";
import { LOCALES, LOCALE_META, type Lang } from "../lib/i18n";

export function mailtoHref(t: Dict) {
  const params = new URLSearchParams({ subject: t.waitlist.subject, body: t.waitlist.body });
  return `mailto:${CONTACT_EMAIL}?${params.toString()}`;
}

/* ---------------------------------------------------------------- ГЕРОЙ -- */

export function Hero({ t, lang }: { t: Dict; lang: Lang }) {
  return (
    <div className="relative flex min-h-[100svh] flex-col items-center px-6 pb-24 pt-[13vh] text-center md:pt-[15vh]">
      <h1 className="font-display text-balance font-bold leading-[1.02] tracking-[-0.035em] text-ink [font-size:clamp(33px,5.15vw,68px)]">
        <Words text={t.hero.title} delay={0.15} />
      </h1>

      <motion.p
        className="mt-4 max-w-[44ch] text-[16.5px] leading-[1.45] text-ink-soft md:mt-5 md:text-[21px]"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.9, delay: 0.55, ease: [0.16, 1, 0.3, 1] }}
      >
        {t.hero.sub1}
        <br className="hidden sm:block" /> {t.hero.sub2}
      </motion.p>

      <motion.div
        className="mt-9 w-full md:mt-11"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.9, delay: 0.75, ease: [0.16, 1, 0.3, 1] }}
      >
        <Generator lang={lang} variant="hero" />
      </motion.div>

      <motion.a
        href="#how"
        className="nav-link mt-8 inline-flex items-center gap-2 text-ink-soft/60 transition hover:text-ink"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.9, delay: 1.05 }}
      >
        {t.hero.cta}
        <svg viewBox="0 0 20 20" fill="none" className="h-3.5 w-3.5">
          <path d="M10 4v12m0 0l-5-5m5 5l5-5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </motion.a>
    </div>
  );
}

/* ------------------------------------------------------------- ПРОБЛЕМА -- */

export function Problem({ t }: { t: Dict }) {
  return (
    <Section id="problem">
      <Reveal>
        <Kicker>{t.problem.kicker}</Kicker>
        <H2>{t.problem.title}</H2>
      </Reveal>

      <div className="mt-12 grid gap-5 lg:grid-cols-[1.15fr_0.85fr]">
        <div className="rounded-3xl border border-ink/12 bg-white/45 p-7 md:p-9">
          <h3 className="nav-link text-ink-soft/70">{t.problem.beforeTitle}</h3>
          <ul className="mt-6 grid gap-x-8 gap-y-3.5 sm:grid-cols-2">
            {t.problem.beforeItems.map((item, i) => (
              <li key={item} className="flex items-start gap-3">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-ink/20 text-[10.5px] text-ink-soft/60">
                  {i + 1}
                </span>
                <span className="text-[14.5px] leading-snug text-ink-soft/85">{item}</span>
              </li>
            ))}
          </ul>
          <p className="mt-7 border-t border-ink/10 pt-5 text-[14px] leading-relaxed text-ink-soft/70">
            {t.problem.beforeFooter}
          </p>
        </div>

        <div className="relative overflow-hidden rounded-3xl bg-forest p-7 text-cream md:p-9">
          <h3 className="nav-link text-lime">{t.problem.afterTitle}</h3>
          <ul className="mt-6 space-y-4">
            {t.problem.afterItems.map((item) => (
              <li key={item} className="flex items-start gap-3">
                <CheckIcon className="mt-0.5 h-5 w-5 shrink-0 text-lime" />
                <span className="text-[16.5px] font-medium leading-snug">{item}</span>
              </li>
            ))}
          </ul>
          <p className="mt-7 border-t border-cream/15 pt-5 text-[14px] leading-relaxed text-cream/75">
            {t.problem.afterFooter}
          </p>
        </div>
      </div>
    </Section>
  );
}

/* ----------------------------------------------------------------- КАК -- */

export function How({ t }: { t: Dict }) {
  return (
    <Section id="how">
      <Reveal>
        <Kicker>{t.how.kicker}</Kicker>
        <H2>{t.how.title}</H2>
        <Lead>{t.how.sub}</Lead>
      </Reveal>

      <Stagger className="mt-14 grid gap-px overflow-hidden rounded-3xl border border-ink/12 bg-ink/10 sm:grid-cols-2 lg:grid-cols-3" gap={0.09}>
        {t.how.steps.map((step) => (
          <StaggerItem key={step.n} className="bg-paper p-7 transition-colors hover:bg-white/60" y={18}>
            <div className="flex items-baseline gap-3">
              <span className="font-display text-[12px] font-bold tracking-[0.12em] text-sage">
                {step.n}
              </span>
              <h3 className="font-display text-[17px] font-bold tracking-[-0.01em] text-ink">
                {step.title}
              </h3>
            </div>
            <p className="mt-3.5 text-[14.5px] leading-relaxed text-ink-soft/85">{step.text}</p>
          </StaggerItem>
        ))}
      </Stagger>
    </Section>
  );
}

/* -------------------------------------------------------------- БЮДЖЕТ -- */

export function Budget({ t }: { t: Dict }) {
  const premium = t.budget.scenes.filter((s) => s.kind === "premium").length;
  const smartShare = Math.round((premium / t.budget.scenes.length) * 100);

  return (
    <Section id="engine">
      <div className="grid gap-14 lg:grid-cols-[0.9fr_1.1fr] lg:gap-16">
        <Reveal>
          <Kicker>{t.budget.kicker}</Kicker>
          <H2>{t.budget.title}</H2>
          <Lead>{t.budget.sub}</Lead>
        </Reveal>

        <div className="rounded-3xl border border-ink/12 bg-white/45 p-7 md:p-9">
          <div className="nav-link text-ink-soft/60">{t.budget.exampleLabel}</div>

          <div className="mt-6 grid grid-cols-5 gap-2.5">
            {t.budget.scenes.map((s) => (
              <div key={s.n} className="text-center">
                <div
                  className={[
                    "flex h-20 items-end justify-center rounded-xl p-2 md:h-24",
                    s.kind === "premium"
                      ? "bg-gradient-to-b from-sage to-forest text-cream"
                      : "border border-ink/15 bg-white/70 text-ink-soft/50",
                  ].join(" ")}
                >
                  <span className="text-[11px] font-semibold">{s.n}</span>
                </div>
                <div className="mt-2 text-[10.5px] leading-tight text-ink-soft/60">{s.label}</div>
              </div>
            ))}
          </div>

          <div className="mt-5 flex flex-wrap items-center gap-x-5 gap-y-2 text-[12.5px] text-ink-soft/75">
            <span className="inline-flex items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-sm bg-forest" />
              {t.budget.premium}
            </span>
            <span className="inline-flex items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-sm border border-ink/20 bg-white" />
              {t.budget.motion}
            </span>
          </div>

          <div className="mt-8 space-y-4 border-t border-ink/10 pt-7">
            <Bar label={t.budget.barNaiveLabel} percent={100} tone="dim" />
            <Bar label={t.budget.barSmartLabel} percent={smartShare} tone="green" />
          </div>

          <p className="mt-7 text-[12.5px] leading-relaxed text-ink-soft/60">{t.budget.footnote}</p>
        </div>
      </div>
    </Section>
  );
}

function Bar({ label, percent, tone }: { label: string; percent: number; tone: "green" | "dim" }) {
  return (
    <div>
      <div className="mb-2 flex items-baseline justify-between gap-4">
        <span className="text-[13px] text-ink-soft/85">{label}</span>
        <span className={`text-[13px] font-semibold ${tone === "green" ? "text-sage" : "text-ink-soft/50"}`}>
          {percent}%
        </span>
      </div>
      <GrowBar
        percent={percent}
        className={tone === "green" ? "bg-gradient-to-r from-sage to-forest" : "bg-ink/25"}
      />
    </div>
  );
}

/* ---------------------------------------------------------- ВОЗМОЖНОСТИ -- */

export function Features({ t }: { t: Dict }) {
  return (
    <Section id="features">
      <Reveal>
        <Kicker>{t.features.kicker}</Kicker>
        <H2>{t.features.title}</H2>
      </Reveal>

      <Stagger className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {t.features.items.map((f, i) => (
          <StaggerItem
            key={f.title}
            className="rounded-3xl border border-ink/12 bg-white/45 p-6 transition-all duration-300 hover:-translate-y-1 hover:border-ink/25 hover:bg-white/70 hover:shadow-[0_18px_50px_-28px_rgba(22,52,26,0.45)]"
          >
            <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-forest text-lime">
              <FeatureIcon d={FEATURE_ICONS[i % FEATURE_ICONS.length]} className="h-5 w-5" />
            </span>
            <h3 className="font-display mt-5 text-[15.5px] font-bold tracking-[-0.01em] text-ink">
              {f.title}
            </h3>
            <p className="mt-2.5 text-[14px] leading-relaxed text-ink-soft/85">{f.text}</p>
          </StaggerItem>
        ))}
      </Stagger>

      <Reveal delay={0.1} className="mt-14">
        <Marquee className="rounded-full border border-ink/12 bg-white/40 py-4" speed={44}>
          {t.features.items.map((f) => (
            <span key={f.title} className="nav-link flex items-center gap-4 whitespace-nowrap text-ink-soft/70">
              {f.title}
              <span className="h-1.5 w-1.5 rounded-full bg-sage" />
            </span>
          ))}
        </Marquee>
      </Reveal>
    </Section>
  );
}

/* --------------------------------------------------------- ДОРОЖНАЯ КАРТА */

export function Roadmap({ t }: { t: Dict }) {
  return (
    <Section id="roadmap">
      <Reveal>
        <Kicker>{t.roadmap.kicker}</Kicker>
        <H2>{t.roadmap.title}</H2>
        <Lead>{t.roadmap.sub}</Lead>
      </Reveal>

      <Stagger className="mt-14 grid gap-5 md:grid-cols-3" gap={0.1}>
        {t.roadmap.columns.map((col, i) => (
          <StaggerItem
            key={col.title}
            className={[
              "rounded-3xl p-7",
              i === 0 ? "bg-forest text-cream" : "border border-ink/12 bg-white/45",
            ].join(" ")}
          >
            <div className="flex items-center justify-between gap-3">
              <h3 className={`font-display text-[16px] font-bold ${i === 0 ? "text-cream" : "text-ink"}`}>
                {col.title}
              </h3>
              <span
                className={[
                  "shrink-0 rounded-full px-3 py-1 text-[10.5px] font-semibold uppercase tracking-[0.08em]",
                  i === 0 ? "bg-lime/20 text-lime" : "bg-ink/8 text-ink-soft/70",
                ].join(" ")}
              >
                {col.state}
              </span>
            </div>
            <ul className="mt-5 space-y-3">
              {col.items.map((item) => (
                <li key={item} className="flex items-start gap-2.5">
                  <span className={`mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full ${i === 0 ? "bg-lime" : "bg-sage"}`} />
                  <span className={`text-[14px] leading-snug ${i === 0 ? "text-cream/85" : "text-ink-soft/85"}`}>
                    {item}
                  </span>
                </li>
              ))}
            </ul>
          </StaggerItem>
        ))}
      </Stagger>
    </Section>
  );
}

/* ---------------------------------------------------------------- ДЕМО -- */

export function Demo({ t }: { t: Dict }) {
  return (
    <Section id="demo">
      <Reveal>
        <Kicker>{t.demo.kicker}</Kicker>
        <H2>{t.demo.title}</H2>
        <Lead>{t.demo.sub}</Lead>
      </Reveal>

      <div className="mt-12 overflow-hidden rounded-3xl border border-ink/12 bg-white/45">
        <div className="relative flex aspect-video items-center justify-center bg-gradient-to-br from-moss via-sage to-lime">
          <div className="text-center">
            <span className="mx-auto flex h-16 w-16 items-center justify-center rounded-full border-[1.5px] border-cream/70 text-cream">
              <PlayIcon className="h-7 w-7" />
            </span>
            <p className="mt-5 text-[15px] font-medium text-cream">{t.demo.placeholder}</p>
          </div>
        </div>
        <p className="px-7 py-5 text-[13.5px] text-ink-soft/70">{t.demo.caption}</p>
      </div>
    </Section>
  );
}

/* -------------------------------------------------------------- КОМАНДА -- */

export function Team({ t }: { t: Dict }) {
  return (
    <Section id="team">
      <Reveal>
        <Kicker>{t.team.kicker}</Kicker>
        <H2>{t.team.title}</H2>
        <Lead>{t.team.sub}</Lead>
      </Reveal>

      <Stagger className="mt-14 grid gap-5 md:grid-cols-3" gap={0.1}>
        {t.team.roles.map((r) => (
          <StaggerItem key={r.role} className="rounded-3xl border border-ink/12 bg-white/45 p-7">
            <div className="nav-link text-sage">{r.role}</div>
            {r.who ? (
              <div className="font-display mt-3 text-[22px] font-bold tracking-[-0.02em] text-ink">
                {r.who}
              </div>
            ) : null}
            <p className={`text-[14.5px] leading-relaxed text-ink-soft/85 ${r.who ? "mt-3" : "mt-4"}`}>
              {r.text}
            </p>
          </StaggerItem>
        ))}
      </Stagger>

      <p className="mt-8 inline-flex rounded-full border border-ink/15 px-4 py-2 text-[12.5px] text-ink-soft/75">
        {t.team.note}
      </p>
    </Section>
  );
}

/* --------------------------------------------------------------- ТАРИФЫ -- */

export function Pricing({ t }: { t: Dict }) {
  return (
    <Section id="pricing">
      <Reveal>
        <Kicker>{t.pricing.kicker}</Kicker>
        <H2>{t.pricing.title}</H2>
        <Lead>{t.pricing.sub}</Lead>
      </Reveal>

      <Stagger className="mt-14 grid gap-5 md:grid-cols-3" gap={0.1}>
        {t.pricing.tiers.map((tier) => (
          <StaggerItem
            key={tier.name}
            className={[
              "flex flex-col rounded-3xl p-7 md:p-8",
              tier.highlight ? "bg-forest text-cream" : "border border-ink/12 bg-white/45",
            ].join(" ")}
          >
            <div className="flex items-center justify-between gap-3">
              <h3 className={`font-display text-[18px] font-bold ${tier.highlight ? "text-cream" : "text-ink"}`}>
                {tier.name}
              </h3>
              <span
                className={[
                  "rounded-full px-3 py-1 text-[10.5px] font-semibold uppercase tracking-[0.08em]",
                  tier.highlight ? "bg-lime/20 text-lime" : "bg-ink/8 text-ink-soft/70",
                ].join(" ")}
              >
                {tier.note}
              </span>
            </div>

            <div
              className={`font-display mt-5 text-[26px] font-bold tracking-[-0.02em] ${tier.highlight ? "text-lime" : "text-ink"}`}
            >
              {tier.price}
            </div>

            <ul className="mt-6 flex-1 space-y-3">
              {tier.items.map((item) => (
                <li key={item} className="flex items-start gap-2.5">
                  <CheckIcon className={`mt-0.5 h-4.5 w-4.5 shrink-0 ${tier.highlight ? "text-lime" : "text-sage"}`} />
                  <span className={`text-[14px] leading-snug ${tier.highlight ? "text-cream/85" : "text-ink-soft/85"}`}>
                    {item}
                  </span>
                </li>
              ))}
            </ul>

            {tier.highlight ? (
              <a
                href={mailtoHref(t)}
                className="nav-link mt-7 inline-flex items-center justify-center gap-2 rounded-full bg-cream px-6 py-3 text-forest transition hover:bg-lime"
              >
                {t.cta.button}
                <ArrowIcon className="h-4 w-4" />
              </a>
            ) : null}
          </StaggerItem>
        ))}
      </Stagger>

      <Reveal>
        <p className="mt-8 max-w-3xl text-[13px] leading-relaxed text-ink-soft/65">{t.pricing.footnote}</p>
      </Reveal>
    </Section>
  );
}

/* -------------------------------------------------------------- ЖУРНАЛ -- */

export function Blog({ t }: { t: Dict }) {
  return (
    <Section id="blog">
      <Reveal>
        <Kicker>{t.blog.kicker}</Kicker>
        <H2>{t.blog.title}</H2>
        <Lead>{t.blog.sub}</Lead>
      </Reveal>

      <Stagger className="mt-12 divide-y divide-ink/10 border-y border-ink/10" gap={0.08}>
        {t.blog.posts.map((post) => (
          <StaggerItem key={post.title} className="grid gap-3 py-7 md:grid-cols-[190px_1fr] md:gap-8">
            <div className="nav-link pt-1 text-ink-soft/55">{post.date}</div>
            <div>
              <h3 className="font-display text-[19px] font-bold tracking-[-0.015em] text-ink">
                {post.title}
              </h3>
              <p className="mt-2.5 max-w-2xl text-[14.5px] leading-relaxed text-ink-soft/85">
                {post.text}
              </p>
            </div>
          </StaggerItem>
        ))}
      </Stagger>
    </Section>
  );
}

/* ----------------------------------------------------------------- FAQ -- */

export function Faq({ t }: { t: Dict }) {
  const [open, setOpen] = useState<number | null>(0);

  return (
    <Section id="faq">
      <Reveal>
        <Kicker>{t.faq.kicker}</Kicker>
        <H2>{t.faq.title}</H2>
      </Reveal>

      <div className="mt-12 max-w-3xl divide-y divide-ink/10 border-y border-ink/10">
        {t.faq.items.map((item, i) => {
          const isOpen = open === i;
          return (
            <div key={item.q}>
              <button
                type="button"
                onClick={() => setOpen(isOpen ? null : i)}
                aria-expanded={isOpen}
                className="flex w-full items-center justify-between gap-6 py-5 text-left"
              >
                <span className="font-display text-[16.5px] font-semibold text-ink">{item.q}</span>
                <span
                  className={[
                    "flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-ink/20 text-ink-soft transition-transform duration-300",
                    isOpen ? "rotate-45 border-ink bg-ink text-cream" : "",
                  ].join(" ")}
                >
                  <svg viewBox="0 0 20 20" fill="none" className="h-4 w-4">
                    <path d="M10 5v10M5 10h10" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
                  </svg>
                </span>
              </button>
              <div
                className={[
                  "grid transition-all duration-300 ease-out",
                  isOpen ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0",
                ].join(" ")}
              >
                <div className="overflow-hidden">
                  <p className="pb-6 pr-10 text-[15px] leading-relaxed text-ink-soft/85">{item.a}</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </Section>
  );
}

/* ----------------------------------------------------------------- CTA -- */

export function Cta({ t }: { t: Dict }) {
  return (
    <Section>
      <div className="relative overflow-hidden rounded-[2rem] bg-forest px-6 py-16 text-center text-cream md:px-16 md:py-24">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -top-32 left-1/2 h-80 w-[700px] -translate-x-1/2 rounded-full bg-[radial-gradient(ellipse_at_center,rgba(195,206,106,0.28),transparent_65%)]"
        />
        <h2 className="font-display relative text-balance text-[28px] font-bold leading-tight tracking-[-0.025em] md:text-[42px]">
          {t.cta.title}
        </h2>
        <p className="relative mx-auto mt-5 max-w-xl text-[16px] leading-relaxed text-cream/80">
          {t.cta.sub}
        </p>
        <div className="relative mt-10">
          <Magnetic strength={0.22}>
            <Pill as="a" href={mailtoHref(t)} size="lg" className="text-cream hover:bg-cream hover:text-forest">
              {t.cta.button}
              <ArrowIcon className="h-4 w-4" />
            </Pill>
          </Magnetic>
          <p className="mt-4 text-[13px] text-cream/60">{t.cta.alt}</p>
        </div>
      </div>
    </Section>
  );
}

/* -------------------------------------------------------------- ПОДВАЛ -- */

export function Footer({ t, lang }: { t: Dict; lang: Lang }) {
  return (
    <footer className="border-t border-ink/10 py-12">
      <div className="container-x">
        <div className="flex flex-col gap-8 md:flex-row md:items-start md:justify-between">
          <p className="max-w-sm text-[14px] leading-relaxed text-ink-soft/80">{t.footer.tagline}</p>

          <div className="flex flex-col gap-6 sm:flex-row sm:gap-14">
            <div className="text-[14px]">
              <div className="nav-link text-ink-soft/55">{t.footer.contact}</div>
              <a
                href={`mailto:${CONTACT_EMAIL}`}
                className="mt-2.5 inline-block text-ink underline decoration-ink/25 underline-offset-4 transition hover:decoration-ink"
              >
                {CONTACT_EMAIL}
              </a>
            </div>

            <div>
              <div className="nav-link text-ink-soft/55">{t.footer.lang}</div>
              <div className="mt-2.5 inline-flex rounded-full border border-ink/15 p-0.5">
                {LOCALES.map((l) => (
                  <a
                    key={l}
                    href={`/${l}`}
                    hrefLang={LOCALE_META[l].htmlLang}
                    onClick={() => {
                      try {
                        document.cookie = `horsteppe-lang=${l}; path=/; max-age=31536000; samesite=lax`;
                      } catch {
                        /* cookie отключены */
                      }
                    }}
                    aria-current={lang === l ? "true" : undefined}
                    title={LOCALE_META[l].native}
                    className={[
                      "nav-link rounded-full px-3.5 py-1.5 transition",
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

        <div className="mt-10 flex flex-wrap items-center justify-between gap-4 border-t border-ink/10 pt-6 text-[12.5px] text-ink-soft/60">
          <span>© {new Date().getFullYear()} Horsteppe. {t.footer.rights}</span>
          <span>{t.footer.orda}</span>
        </div>
      </div>
    </footer>
  );
}
