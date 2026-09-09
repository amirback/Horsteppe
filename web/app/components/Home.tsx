"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useScroll, useSpring, useTransform, useMotionValue } from "motion/react";
import { content } from "../lib/content";
import type { Lang } from "../lib/i18n";
import { Mesh } from "./Mesh";
import { Generator } from "./Generator";
import { Nav } from "./Nav";
import { Footer } from "./Footer";
import { motion, Words, Reveal, Stagger, StaggerItem } from "./motion";

const EASE = [0.16, 1, 0.3, 1] as const;

export function Home({ lang }: { lang: Lang }) {
  const t = content[lang];

  return (
    <>
      <Nav lang={lang} overlay />

      <header id="top" className="relative isolate">
        <Mesh />
        <PointerLight />

        <div className="container-x relative flex min-h-[100svh] flex-col items-center justify-center px-5 py-28 text-center sm:py-32">
          <h1 className="font-display text-balance font-bold leading-[1.04] tracking-[-0.035em] text-ink [font-size:clamp(30px,6.4vw,62px)]">
            <Words text={t.hero.title} delay={0.1} />
          </h1>

          <motion.p
            className="mx-auto mt-4 max-w-[34ch] text-[15px] leading-[1.45] text-ink-soft sm:text-[18px] md:mt-5"
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.85, delay: 0.5, ease: EASE }}
          >
            {t.hero.sub}
          </motion.p>

          <motion.div
            className="mt-8 w-full sm:mt-10"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.85, delay: 0.68, ease: EASE }}
          >
            <Generator lang={lang} variant="hero" />
          </motion.div>

          <motion.a
            href="#how"
            className="nav-link mt-8 inline-flex items-center gap-2 text-ink-soft/60 transition hover:text-ink"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.95 }}
          >
            {t.hero.scroll}
            <motion.span
              animate={{ y: [0, 4, 0] }}
              transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
            >
              <svg viewBox="0 0 20 20" fill="none" className="h-3.5 w-3.5">
                <path d="M10 4v12m0 0l-5-5m5 5l5-5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </motion.span>
          </motion.a>
        </div>
      </header>

      <main>
        <Steps lang={lang} />

        <section className="container-x py-16 md:py-24">
          <Stagger className="grid gap-4 md:grid-cols-3 md:gap-5">
            {t.values.map((v) => (
              <StaggerItem
                key={v.title}
                className="rounded-3xl border border-ink/12 bg-white/45 p-6 transition-all duration-300 hover:-translate-y-1 hover:border-ink/25 hover:shadow-[0_18px_50px_-30px_rgba(22,52,26,0.5)] md:p-7"
              >
                <h3 className="font-display text-[16.5px] font-bold tracking-[-0.01em] text-ink">{v.title}</h3>
                <p className="mt-2.5 text-[14px] leading-relaxed text-ink-soft/85">{v.text}</p>
              </StaggerItem>
            ))}
          </Stagger>
        </section>

        <section className="container-x pb-16 md:pb-24">
          <Reveal>
            <div className="mx-auto max-w-2xl divide-y divide-ink/10 border-y border-ink/10">
              {t.faq.map((item) => (
                <Faq key={item.q} q={item.q} a={item.a} />
              ))}
            </div>
          </Reveal>
        </section>

        <section className="container-x pb-20 md:pb-28">
          <Reveal>
            <div className="relative overflow-hidden rounded-[28px] bg-forest px-6 py-12 text-center text-cream md:px-14 md:py-16">
              <div
                aria-hidden="true"
                className="pointer-events-none absolute -top-24 left-1/2 h-56 w-[520px] -translate-x-1/2 rounded-full bg-[radial-gradient(ellipse_at_center,rgba(195,206,106,0.3),transparent_65%)]"
              />
              <h2 className="font-display relative text-balance text-[24px] font-bold leading-tight tracking-[-0.02em] md:text-[34px]">
                {t.hero.sub}
              </h2>
              <Link
                href="#top"
                className="nav-link relative mt-7 inline-flex items-center gap-2 rounded-full bg-cream px-7 py-3.5 text-forest transition hover:bg-lime"
              >
                {t.nav.cta}
              </Link>
            </div>
          </Reveal>
        </section>
      </main>

      <Footer lang={lang} />
    </>
  );
}

/* --------------------------------------------------- шаги с линией -- */

/**
 * Три шага, соединённые линией, которая чертится по мере прокрутки.
 * На широком экране линия горизонтальная, на узком — вертикальная:
 * это один и тот же прогресс, просто отрисованный по-разному.
 */
function Steps({ lang }: { lang: Lang }) {
  const t = content[lang];
  const ref = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start 0.85", "center 0.55"] });
  const grow = useSpring(scrollYProgress, { stiffness: 90, damping: 24, restDelta: 0.001 });

  return (
    <section ref={ref} id="how" className="container-x scroll-mt-24 py-16 md:py-24">
      <div className="relative">
        <div aria-hidden="true" className="absolute left-[15px] top-2 hidden h-[calc(100%-1rem)] w-px bg-ink/10 sm:block md:left-0 md:top-[15px] md:h-px md:w-full">
          <motion.div
            className="h-full w-full origin-top bg-sage md:origin-left"
            style={{ scaleY: grow, scaleX: grow }}
          />
        </div>

        <ol className="grid gap-8 sm:gap-9 md:grid-cols-3 md:gap-6">
          {t.steps.map((step, i) => (
            <motion.li
              key={step.n}
              className="relative pl-11 sm:pl-12 md:pl-0 md:pt-11"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-15% 0px" }}
              transition={{ duration: 0.7, delay: i * 0.12, ease: EASE }}
            >
              <span className="absolute left-0 top-0 flex h-[31px] w-[31px] items-center justify-center rounded-full border border-ink/15 bg-paper font-display text-[11px] font-bold tracking-[0.06em] text-sage">
                {step.n}
              </span>
              <h3 className="font-display text-[17px] font-bold tracking-[-0.01em] text-ink">{step.title}</h3>
              <p className="mt-2 text-[14px] leading-relaxed text-ink-soft/85">{step.text}</p>
            </motion.li>
          ))}
        </ol>
      </div>
    </section>
  );
}

/* -------------------------------------------------------------- FAQ -- */

function Faq({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-5 py-4 text-left"
      >
        <span className="font-display text-[15px] font-semibold text-ink sm:text-[16px]">{q}</span>
        <span
          className={[
            "flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-ink/20 text-ink-soft transition-transform duration-300",
            open ? "rotate-45 border-ink bg-ink text-cream" : "",
          ].join(" ")}
        >
          <svg viewBox="0 0 20 20" fill="none" className="h-3.5 w-3.5">
            <path d="M10 5v10M5 10h10" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
          </svg>
        </span>
      </button>
      <div className={["grid transition-all duration-300 ease-out", open ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"].join(" ")}>
        <div className="overflow-hidden">
          <p className="pb-5 pr-8 text-[14px] leading-relaxed text-ink-soft/85">{a}</p>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------- свет за курсором -- */

/** Мягкое пятно света, следующее за курсором. Только там, где есть мышь. */
function PointerLight() {
  const x = useSpring(useMotionValue(-500), { stiffness: 60, damping: 22, mass: 0.6 });
  const y = useSpring(useMotionValue(-500), { stiffness: 60, damping: 22, mass: 0.6 });
  const left = useTransform(x, (v) => `${v - 260}px`);
  const top = useTransform(y, (v) => `${v - 260}px`);
  const [fine, setFine] = useState(false);

  useEffect(() => {
    if (!window.matchMedia("(hover: hover) and (pointer: fine)").matches) return;
    setFine(true);
    const onMove = (e: PointerEvent) => {
      x.set(e.clientX);
      y.set(e.clientY);
    };
    window.addEventListener("pointermove", onMove, { passive: true });
    return () => window.removeEventListener("pointermove", onMove);
  }, [x, y]);

  if (!fine) return null;

  return (
    <motion.div
      aria-hidden="true"
      style={{ left, top }}
      className="pointer-events-none absolute z-0 h-[520px] w-[520px] rounded-full bg-[radial-gradient(circle,rgba(247,246,233,0.22),transparent_62%)] mix-blend-soft-light"
    />
  );
}
