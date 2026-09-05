"use client";

import { useEffect, useState } from "react";
import type { Dict } from "../lib/content";
import { CONTACT_EMAIL } from "../lib/content";
import {
  ArrowIcon,
  CheckIcon,
  DotIcon,
  FEATURE_ICONS,
  FeatureIcon,
  H2,
  Kicker,
  Lead,
  PlayIcon,
  Section,
} from "./ui";

export function mailtoHref(t: Dict) {
  const params = new URLSearchParams({
    subject: t.waitlist.subject,
    body: t.waitlist.body,
  });
  return `mailto:${CONTACT_EMAIL}?${params.toString()}`;
}

/* ---------------------------------------------------------------- HERO -- */

export function Hero({ t }: { t: Dict }) {
  const [stage, setStage] = useState(0);

  useEffect(() => {
    const id = window.setInterval(() => {
      setStage((s) => (s + 1) % (t.hero.stages.length + 1));
    }, 1400);
    return () => window.clearInterval(id);
  }, [t.hero.stages.length]);

  return (
    <header className="relative overflow-hidden pt-28 pb-16 md:pt-36 md:pb-24">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 -z-10"
      >
        <div className="drift absolute -top-40 left-1/2 h-[520px] w-[900px] -translate-x-1/2 rounded-full bg-[radial-gradient(ellipse_at_center,rgba(233,161,59,0.16),transparent_65%)]" />
        <div className="absolute -bottom-32 -left-24 h-[420px] w-[520px] rounded-full bg-[radial-gradient(ellipse_at_center,rgba(108,123,217,0.12),transparent_68%)]" />
        <div className="absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-line to-transparent" />
      </div>

      <div className="container-x">
        <div className="grid items-center gap-14 lg:grid-cols-[1.05fr_0.95fr] lg:gap-16">
          <div className="fade-up">
            <span className="inline-flex items-center gap-2 rounded-full border border-line bg-surface/70 px-3.5 py-1.5 text-[12.5px] text-muted">
              <span className="relative flex h-1.5 w-1.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber opacity-70" />
                <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-amber" />
              </span>
              {t.hero.badge}
            </span>

            <h1 className="mt-6 text-balance text-[40px] font-semibold leading-[1.05] tracking-[-0.032em] text-cream sm:text-[52px] lg:text-[60px]">
              {t.hero.title}
              <br />
              <span className="bg-gradient-to-r from-amber-soft via-amber to-ember bg-clip-text text-transparent">
                {t.hero.titleAccent}
              </span>
            </h1>

            <p className="mt-6 max-w-xl text-[16.5px] leading-relaxed text-muted md:text-[17.5px]">
              {t.hero.sub}
            </p>

            <div className="mt-9 flex flex-col gap-3 sm:flex-row sm:items-center">
              <a
                href={mailtoHref(t)}
                className="glow-amber inline-flex items-center justify-center gap-2 rounded-xl bg-amber px-6 py-3.5 text-[15px] font-semibold text-[#1a1206] transition hover:bg-amber-soft"
              >
                {t.hero.ctaPrimary}
                <ArrowIcon className="h-4 w-4" />
              </a>
              <a
                href="#how"
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-line bg-surface/60 px-6 py-3.5 text-[15px] font-medium text-cream transition hover:border-muted-2 hover:bg-surface"
              >
                {t.hero.ctaSecondary}
              </a>
            </div>

            <p className="mt-5 text-[13.5px] text-muted-2">{t.hero.note}</p>
          </div>

          <div className="fade-up" style={{ animationDelay: "120ms" }}>
            <StudioMock t={t} stage={stage} />
          </div>
        </div>
      </div>
    </header>
  );
}

function StudioMock({ t, stage }: { t: Dict; stage: number }) {
  const done = stage;
  const total = t.hero.stages.length;
  const isComplete = done >= total;

  return (
    <div className="relative">
      <div className="grain relative overflow-hidden rounded-2xl border border-line bg-surface/90 shadow-[0_40px_120px_-40px_rgba(0,0,0,0.9)]">
        <div className="flex items-center gap-2 border-b border-line-soft px-4 py-3">
          <span className="h-2.5 w-2.5 rounded-full bg-[#3a3742]" />
          <span className="h-2.5 w-2.5 rounded-full bg-[#3a3742]" />
          <span className="h-2.5 w-2.5 rounded-full bg-[#3a3742]" />
          <span className="ml-2 text-[12px] text-muted-2">horsteppe.com</span>
        </div>

        <div className="p-5 md:p-6">
          <div className="rounded-xl border border-line bg-ink-2 px-4 py-3.5 text-[14px] text-muted">
            {t.hero.promptPlaceholder}
          </div>

          <div className="mt-3 grid grid-cols-2 gap-2.5">
            {(
              [
                ["style", t.hero.fields.style, t.hero.fieldValues.style],
                ["duration", t.hero.fields.duration, t.hero.fieldValues.duration],
                ["language", t.hero.fields.language, t.hero.fieldValues.language],
                ["format", t.hero.fields.format, t.hero.fieldValues.format],
              ] as const
            ).map(([key, label, value]) => (
              <div
                key={key}
                className="rounded-lg border border-line bg-ink-2/70 px-3 py-2.5"
              >
                <div className="text-[10.5px] uppercase tracking-[0.12em] text-muted-2">
                  {label}
                </div>
                <div className="mt-1 text-[13.5px] text-cream">{value}</div>
              </div>
            ))}
          </div>

          <div className="mt-3.5 rounded-xl bg-amber px-4 py-3 text-center text-[14px] font-semibold text-[#1a1206]">
            {t.hero.generate}
          </div>

          <div className="mt-5 space-y-2.5 border-t border-line-soft pt-5">
            {t.hero.stages.map((s, i) => {
              const state =
                i < done ? "done" : i === done && !isComplete ? "active" : "idle";
              return (
                <div key={s} className="flex items-center gap-3">
                  <span
                    className={[
                      "flex h-5 w-5 shrink-0 items-center justify-center rounded-full border transition-colors duration-500",
                      state === "done"
                        ? "border-amber/60 bg-amber/15 text-amber"
                        : state === "active"
                          ? "border-amber bg-amber/10 text-amber"
                          : "border-line text-muted-2",
                    ].join(" ")}
                  >
                    {state === "done" ? (
                      <CheckIcon className="h-3.5 w-3.5" />
                    ) : (
                      <DotIcon
                        className={`h-3 w-3 ${state === "active" ? "animate-pulse" : "opacity-40"}`}
                      />
                    )}
                  </span>
                  <span
                    className={[
                      "text-[13.5px] transition-colors duration-500",
                      state === "idle" ? "text-muted-2" : "text-cream",
                    ].join(" ")}
                  >
                    {s}
                  </span>
                </div>
              );
            })}
          </div>

          <div className="mt-5 overflow-hidden rounded-xl border border-line bg-ink-2">
            <div
              className={[
                "flex aspect-video items-center justify-center transition-opacity duration-700",
                isComplete ? "opacity-100" : "opacity-40",
              ].join(" ")}
            >
              <span className="flex h-12 w-12 items-center justify-center rounded-full border border-amber/40 bg-amber/10 text-amber">
                <PlayIcon className="h-6 w-6" />
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------- PROBLEM -- */

export function Problem({ t }: { t: Dict }) {
  return (
    <Section id="problem">
      <Kicker>{t.problem.kicker}</Kicker>
      <H2>{t.problem.title}</H2>

      <div className="mt-12 grid gap-5 lg:grid-cols-[1.15fr_0.85fr]">
        <div className="rounded-2xl border border-line bg-surface/40 p-6 md:p-8">
          <h3 className="text-[15px] font-semibold text-muted">
            {t.problem.beforeTitle}
          </h3>
          <ul className="mt-6 grid gap-x-8 gap-y-3.5 sm:grid-cols-2">
            {t.problem.beforeItems.map((item, i) => (
              <li key={item} className="flex items-start gap-3">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded border border-line text-[11px] text-muted-2">
                  {i + 1}
                </span>
                <span className="text-[14.5px] leading-snug text-muted">
                  {item}
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-7 border-t border-line-soft pt-5 text-[14px] leading-relaxed text-muted-2">
            {t.problem.beforeFooter}
          </p>
        </div>

        <div className="relative overflow-hidden rounded-2xl border border-amber/25 bg-gradient-to-b from-amber/[0.07] to-transparent p-6 md:p-8">
          <h3 className="text-[15px] font-semibold text-amber">
            {t.problem.afterTitle}
          </h3>
          <ul className="mt-6 space-y-4">
            {t.problem.afterItems.map((item) => (
              <li key={item} className="flex items-start gap-3">
                <CheckIcon className="mt-0.5 h-5 w-5 shrink-0 text-amber" />
                <span className="text-[16px] font-medium leading-snug text-cream">
                  {item}
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-7 border-t border-amber/15 pt-5 text-[14px] leading-relaxed text-muted">
            {t.problem.afterFooter}
          </p>
        </div>
      </div>
    </Section>
  );
}

/* ----------------------------------------------------------------- HOW -- */

export function How({ t }: { t: Dict }) {
  return (
    <Section id="how" className="border-t border-line-soft">
      <Kicker>{t.how.kicker}</Kicker>
      <H2>{t.how.title}</H2>
      <Lead>{t.how.sub}</Lead>

      <ol className="mt-14 grid gap-px overflow-hidden rounded-2xl border border-line bg-line sm:grid-cols-2 lg:grid-cols-3">
        {t.how.steps.map((step) => (
          <li key={step.n} className="group bg-ink p-7 transition-colors hover:bg-surface/50">
            <div className="flex items-baseline gap-3">
              <span className="text-[12px] font-semibold tracking-[0.14em] text-amber">
                {step.n}
              </span>
              <h3 className="text-[17px] font-semibold tracking-[-0.01em] text-cream">
                {step.title}
              </h3>
            </div>
            <p className="mt-3.5 text-[14.5px] leading-relaxed text-muted">
              {step.text}
            </p>
          </li>
        ))}
      </ol>
    </Section>
  );
}

/* -------------------------------------------------------------- BUDGET -- */

export function Budget({ t }: { t: Dict }) {
  const premiumCount = t.budget.scenes.filter((s) => s.kind === "premium").length;
  const smartShare = Math.round((premiumCount / t.budget.scenes.length) * 100);

  return (
    <Section id="engine" className="border-t border-line-soft">
      <div className="grid gap-14 lg:grid-cols-[0.9fr_1.1fr] lg:gap-16">
        <div>
          <Kicker>{t.budget.kicker}</Kicker>
          <H2>{t.budget.title}</H2>
          <Lead>{t.budget.sub}</Lead>
        </div>

        <div className="rounded-2xl border border-line bg-surface/40 p-6 md:p-8">
          <div className="text-[12.5px] uppercase tracking-[0.13em] text-muted-2">
            {t.budget.exampleLabel}
          </div>

          <div className="mt-6 grid grid-cols-5 gap-2">
            {t.budget.scenes.map((s) => (
              <div key={s.n} className="text-center">
                <div
                  className={[
                    "flex h-20 items-end justify-center rounded-lg border p-2 md:h-24",
                    s.kind === "premium"
                      ? "border-amber/45 bg-gradient-to-b from-amber/25 to-amber/5"
                      : "border-line bg-ink-2",
                  ].join(" ")}
                >
                  <span
                    className={[
                      "text-[11px] font-semibold",
                      s.kind === "premium" ? "text-amber" : "text-muted-2",
                    ].join(" ")}
                  >
                    {s.n}
                  </span>
                </div>
                <div className="mt-2 text-[10.5px] leading-tight text-muted-2">
                  {s.label}
                </div>
              </div>
            ))}
          </div>

          <div className="mt-5 flex flex-wrap items-center gap-x-5 gap-y-2 text-[12.5px]">
            <span className="inline-flex items-center gap-2 text-muted">
              <span className="h-2.5 w-2.5 rounded-sm border border-amber/45 bg-amber/25" />
              {t.budget.premium}
            </span>
            <span className="inline-flex items-center gap-2 text-muted">
              <span className="h-2.5 w-2.5 rounded-sm border border-line bg-ink-2" />
              {t.budget.motion}
            </span>
          </div>

          <div className="mt-8 space-y-4 border-t border-line-soft pt-7">
            <Bar label={t.budget.barNaiveLabel} percent={100} tone="dim" />
            <Bar label={t.budget.barSmartLabel} percent={smartShare} tone="amber" />
          </div>

          <p className="mt-7 text-[12.5px] leading-relaxed text-muted-2">
            {t.budget.footnote}
          </p>
        </div>
      </div>
    </Section>
  );
}

function Bar({
  label,
  percent,
  tone,
}: {
  label: string;
  percent: number;
  tone: "amber" | "dim";
}) {
  return (
    <div>
      <div className="mb-2 flex items-baseline justify-between gap-4">
        <span className="text-[13px] text-muted">{label}</span>
        <span
          className={`text-[13px] font-semibold ${tone === "amber" ? "text-amber" : "text-muted-2"}`}
        >
          {percent}%
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-ink-2">
        <div
          className={
            tone === "amber"
              ? "h-full rounded-full bg-gradient-to-r from-amber to-ember"
              : "h-full rounded-full bg-[#33303c]"
          }
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}

/* ------------------------------------------------------------ FEATURES -- */

export function Features({ t }: { t: Dict }) {
  return (
    <Section id="features" className="border-t border-line-soft">
      <Kicker>{t.features.kicker}</Kicker>
      <H2>{t.features.title}</H2>

      <div className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {t.features.items.map((f, i) => (
          <div
            key={f.title}
            className="rounded-2xl border border-line bg-surface/35 p-6 transition-colors hover:border-muted-2/60 hover:bg-surface/60"
          >
            <span className="flex h-10 w-10 items-center justify-center rounded-xl border border-amber/25 bg-amber/10 text-amber">
              <FeatureIcon
                d={FEATURE_ICONS[i % FEATURE_ICONS.length]}
                className="h-5 w-5"
              />
            </span>
            <h3 className="mt-5 text-[15.5px] font-semibold tracking-[-0.01em] text-cream">
              {f.title}
            </h3>
            <p className="mt-2.5 text-[14px] leading-relaxed text-muted">
              {f.text}
            </p>
          </div>
        ))}
      </div>
    </Section>
  );
}

/* ------------------------------------------------------------- ROADMAP -- */

export function Roadmap({ t }: { t: Dict }) {
  return (
    <Section id="roadmap" className="border-t border-line-soft">
      <Kicker>{t.roadmap.kicker}</Kicker>
      <H2>{t.roadmap.title}</H2>
      <Lead>{t.roadmap.sub}</Lead>

      <div className="mt-14 grid gap-5 md:grid-cols-3">
        {t.roadmap.columns.map((col, i) => (
          <div
            key={col.title}
            className={[
              "rounded-2xl border p-6 md:p-7",
              i === 0
                ? "border-amber/25 bg-gradient-to-b from-amber/[0.06] to-transparent"
                : "border-line bg-surface/35",
            ].join(" ")}
          >
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-[16px] font-semibold text-cream">{col.title}</h3>
              <span
                className={[
                  "shrink-0 rounded-full border px-2.5 py-1 text-[11px]",
                  i === 0
                    ? "border-amber/35 bg-amber/10 text-amber"
                    : "border-line bg-ink-2 text-muted-2",
                ].join(" ")}
              >
                {col.state}
              </span>
            </div>
            <ul className="mt-5 space-y-3">
              {col.items.map((item) => (
                <li key={item} className="flex items-start gap-2.5">
                  <span
                    className={[
                      "mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full",
                      i === 0 ? "bg-amber" : "bg-muted-2",
                    ].join(" ")}
                  />
                  <span className="text-[14px] leading-snug text-muted">{item}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </Section>
  );
}

/* ---------------------------------------------------------------- DEMO -- */

export function Demo({ t }: { t: Dict }) {
  return (
    <Section id="demo" className="border-t border-line-soft">
      <Kicker>{t.demo.kicker}</Kicker>
      <H2>{t.demo.title}</H2>
      <Lead>{t.demo.sub}</Lead>

      <div className="mt-12 overflow-hidden rounded-2xl border border-line bg-surface/40">
        <div className="grain relative flex aspect-video items-center justify-center bg-[radial-gradient(ellipse_at_center,rgba(233,161,59,0.08),transparent_60%)]">
          <div className="text-center">
            <span className="mx-auto flex h-16 w-16 items-center justify-center rounded-full border border-amber/35 bg-amber/10 text-amber">
              <PlayIcon className="h-7 w-7" />
            </span>
            <p className="mt-5 text-[15px] font-medium text-cream">
              {t.demo.placeholder}
            </p>
          </div>
        </div>
        <p className="border-t border-line-soft px-6 py-4 text-[13.5px] text-muted-2">
          {t.demo.caption}
        </p>
      </div>
    </Section>
  );
}

/* ----------------------------------------------------------------- FAQ -- */

export function Faq({ t }: { t: Dict }) {
  const [open, setOpen] = useState<number | null>(0);

  return (
    <Section id="faq" className="border-t border-line-soft">
      <Kicker>{t.faq.kicker}</Kicker>
      <H2>{t.faq.title}</H2>

      <div className="mt-12 max-w-3xl divide-y divide-line-soft border-y border-line-soft">
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
                <span className="text-[16px] font-medium text-cream">{item.q}</span>
                <span
                  className={[
                    "flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-line text-muted transition-transform duration-300",
                    isOpen ? "rotate-45 border-amber/50 text-amber" : "",
                  ].join(" ")}
                >
                  <svg viewBox="0 0 20 20" fill="none" className="h-4 w-4">
                    <path
                      d="M10 5v10M5 10h10"
                      stroke="currentColor"
                      strokeWidth="1.6"
                      strokeLinecap="round"
                    />
                  </svg>
                </span>
              </button>
              <div
                className={[
                  "grid transition-all duration-300 ease-out",
                  isOpen
                    ? "grid-rows-[1fr] opacity-100"
                    : "grid-rows-[0fr] opacity-0",
                ].join(" ")}
              >
                <div className="overflow-hidden">
                  <p className="pb-6 pr-12 text-[15px] leading-relaxed text-muted">
                    {item.a}
                  </p>
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
    <Section className="border-t border-line-soft">
      <div className="grain relative overflow-hidden rounded-3xl border border-line bg-gradient-to-br from-surface to-ink-2 px-6 py-14 text-center md:px-16 md:py-20">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -top-24 left-1/2 h-64 w-[600px] -translate-x-1/2 rounded-full bg-[radial-gradient(ellipse_at_center,rgba(233,161,59,0.2),transparent_65%)]"
        />
        <h2 className="relative text-balance text-[28px] font-semibold leading-tight tracking-[-0.025em] text-cream md:text-[40px]">
          {t.cta.title}
        </h2>
        <p className="relative mx-auto mt-5 max-w-xl text-[16px] leading-relaxed text-muted">
          {t.cta.sub}
        </p>
        <div className="relative mt-9">
          <a
            href={mailtoHref(t)}
            className="glow-amber inline-flex items-center justify-center gap-2 rounded-xl bg-amber px-7 py-3.5 text-[15px] font-semibold text-[#1a1206] transition hover:bg-amber-soft"
          >
            {t.cta.button}
            <ArrowIcon className="h-4 w-4" />
          </a>
          <p className="mt-4 text-[13px] text-muted-2">{t.cta.alt}</p>
        </div>
      </div>
    </Section>
  );
}

/* -------------------------------------------------------------- FOOTER -- */

export function Footer({ t }: { t: Dict }) {
  return (
    <footer className="border-t border-line-soft py-12">
      <div className="container-x">
        <div className="flex flex-col gap-8 md:flex-row md:items-start md:justify-between">
          <div className="max-w-sm">
            <p className="text-[14px] leading-relaxed text-muted">{t.footer.tagline}</p>
            <p className="mt-4 inline-flex items-center gap-2 rounded-full border border-line bg-surface/50 px-3 py-1.5 text-[12px] text-muted-2">
              {t.footer.orda}
            </p>
          </div>

          <div className="text-[14px]">
            <div className="text-[12px] uppercase tracking-[0.13em] text-muted-2">
              {t.footer.contact}
            </div>
            <a
              href={`mailto:${CONTACT_EMAIL}`}
              className="mt-2 inline-block text-cream underline decoration-line underline-offset-4 transition hover:decoration-amber"
            >
              {CONTACT_EMAIL}
            </a>
          </div>
        </div>

        <div className="mt-10 border-t border-line-soft pt-6 text-[12.5px] text-muted-2">
          © {new Date().getFullYear()} Horsteppe. {t.footer.rights}
        </div>
      </div>
    </footer>
  );
}
