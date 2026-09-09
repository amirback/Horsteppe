"use client";

import type { ReactNode } from "react";
import Image from "next/image";
import { motion } from "motion/react";

/* ------------------------------------------------------------------ ЛОГОТИП */

/**
 * Фирменный знак — файл основателя с прозрачным фоном.
 * `object-contain` вместо `cover`: пропорции у знака не квадратные,
 * и обрезка съела бы кончик гривы.
 */
export function Mark({ className = "", animate = false }: { className?: string; animate?: boolean }) {
  return (
    <motion.span
      className={`relative block ${className}`}
      initial={animate ? { opacity: 0, scale: 0.8, rotate: -8 } : false}
      animate={animate ? { opacity: 1, scale: 1, rotate: 0 } : undefined}
      transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
    >
      <Image src="/logo.png" alt="" fill sizes="56px" priority className="object-contain" />
    </motion.span>
  );
}

export function Logo({ className = "", animate = false }: { className?: string; animate?: boolean }) {
  return (
    <span className={`inline-flex items-center gap-2 text-ink sm:gap-2.5 ${className}`}>
      <Mark className="h-10 w-11 shrink-0 sm:h-12 sm:w-14" animate={animate} />
      <span className="font-display text-[20px] font-bold tracking-[-0.022em] sm:text-[24px]">
        Horsteppe
      </span>
    </span>
  );
}

/* --------------------------------------------------------------- ПРИМИТИВЫ */

export function Section({
  id,
  children,
  className = "",
}: {
  id?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section id={id} className={`scroll-mt-32 py-20 md:py-28 ${className}`}>
      <div className="container-x">{children}</div>
    </section>
  );
}

export function Kicker({ children }: { children: ReactNode }) {
  return (
    <div className="mb-4 inline-flex items-center gap-2.5 nav-link text-ink-soft/70">
      <span className="h-px w-7 bg-ink-soft/40" />
      {children}
    </div>
  );
}

export function H2({ children }: { children: ReactNode }) {
  return (
    <h2 className="font-display max-w-3xl text-balance text-[30px] font-bold leading-[1.1] tracking-[-0.02em] text-ink md:text-[42px]">
      {children}
    </h2>
  );
}

export function Lead({ children }: { children: ReactNode }) {
  return (
    <p className="mt-5 max-w-2xl text-[16.5px] leading-relaxed text-ink-soft/85">
      {children}
    </p>
  );
}

/** Контурная «пилюля» — базовый элемент макета: кнопка, поиск, метка. */
export function Pill({
  as = "span",
  href,
  onClick,
  children,
  className = "",
  size = "md",
}: {
  as?: "span" | "a" | "button";
  href?: string;
  onClick?: () => void;
  children: ReactNode;
  className?: string;
  size?: "sm" | "md" | "lg" | "hero";
}) {
  const pad =
    size === "hero"
      ? "min-w-[300px] px-12 py-[22px] text-[13px]"
      : size === "lg"
      ? "px-12 py-4 text-[13px]"
      : size === "sm"
        ? "px-4 py-2 text-[11.5px]"
        : "px-7 py-2.5 text-[13px]";
  const cls = `nav-link inline-flex items-center justify-center gap-2.5 rounded-full border-[1.5px] border-current transition ${pad} ${className}`;

  if (as === "a") {
    return (
      <a href={href} onClick={onClick} className={cls}>
        {children}
      </a>
    );
  }
  if (as === "button") {
    return (
      <button type="button" onClick={onClick} className={cls}>
        {children}
      </button>
    );
  }
  return <span className={cls}>{children}</span>;
}

/* ----------------------------------------------------------------- ИКОНКИ */

export function SearchIcon({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 20 20" fill="none" className={className} aria-hidden="true">
      <circle cx="9" cy="9" r="5.4" stroke="currentColor" strokeWidth="1.7" />
      <path
        d="M13.2 13.2L17 17"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function CheckIcon({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 20 20" fill="none" className={className} aria-hidden="true">
      <path
        d="M4.5 10.5l3.5 3.5 7.5-8"
        stroke="currentColor"
        strokeWidth="1.9"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function ArrowIcon({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 20 20" fill="none" className={className} aria-hidden="true">
      <path
        d="M4 10h11m0 0l-4.5-4.5M15 10l-4.5 4.5"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function PlayIcon({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden="true">
      <path d="M9 7.5v9l7.5-4.5L9 7.5z" fill="currentColor" />
    </svg>
  );
}

export const FEATURE_ICONS = [
  "M4 6.5h16M4 6.5A1.5 1.5 0 015.5 5h13A1.5 1.5 0 0120 6.5M4 6.5v11A1.5 1.5 0 005.5 19h13a1.5 1.5 0 001.5-1.5v-11M9 5v14M15 5v14",
  "M4 5h16v14H4V5zm0 5h16M9 10v9",
  "M12 4v16M8.5 8.5A3 3 0 0111.5 6h1a3 3 0 010 6h-1a3 3 0 000 6h1a3 3 0 003-2.5",
  "M4.5 9.5A7.5 7.5 0 0117 6m2.5 8.5A7.5 7.5 0 017 18M4.5 5v4.5H9M19.5 19v-4.5H15",
  "M12 4a3 3 0 013 3v5a3 3 0 01-6 0V7a3 3 0 013-3zM6 11.5a6 6 0 0012 0M12 17.5V21",
  "M4 7h16M4 12h10M4 17h16M17.5 12l2.5 2.5-2.5 2.5",
  "M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3zm0 0v18m8-13.5L12 12 4 7.5",
  "M12 3l7.5 3v6c0 4.5-3 7.5-7.5 9-4.5-1.5-7.5-4.5-7.5-9V6L12 3zm-3 9l2 2 4-4",
];

export function FeatureIcon({ d, className = "" }: { d: string; className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden="true">
      <path
        d={d}
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
