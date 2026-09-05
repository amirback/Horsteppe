import type { ReactNode } from "react";

export function Logo({ className = "" }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2.5 ${className}`}>
      <Mark className="h-7 w-7" />
      <span className="text-[17px] font-semibold tracking-[-0.02em] text-cream">
        Horsteppe
      </span>
    </span>
  );
}

export function Mark({ className = "" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 32 32"
      fill="none"
      className={className}
      aria-hidden="true"
      role="presentation"
    >
      <rect width="32" height="32" rx="9" fill="#16151c" />
      <rect
        x="0.5"
        y="0.5"
        width="31"
        height="31"
        rx="8.5"
        stroke="#2a2732"
      />
      <circle cx="16" cy="13.5" r="5" fill="#e9a13b" />
      <path
        d="M5 21.5h22M8 25h16"
        stroke="#f5c887"
        strokeWidth="1.6"
        strokeLinecap="round"
        opacity="0.75"
      />
      <path
        d="M11 18.5c1.6-1.2 3.2-1.8 5-1.8s3.4.6 5 1.8"
        stroke="#08070a"
        strokeWidth="1.6"
        strokeLinecap="round"
        opacity="0.35"
      />
    </svg>
  );
}

export function Kicker({ children }: { children: ReactNode }) {
  return (
    <div className="mb-4 inline-flex items-center gap-2 text-[12px] font-medium uppercase tracking-[0.16em] text-amber">
      <span className="h-px w-6 bg-amber/50" />
      {children}
    </div>
  );
}

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
    <section id={id} className={`scroll-mt-24 py-20 md:py-28 ${className}`}>
      <div className="container-x">{children}</div>
    </section>
  );
}

export function H2({ children }: { children: ReactNode }) {
  return (
    <h2 className="max-w-3xl text-balance text-[30px] font-semibold leading-[1.12] tracking-[-0.025em] text-cream md:text-[44px]">
      {children}
    </h2>
  );
}

export function Lead({ children }: { children: ReactNode }) {
  return (
    <p className="mt-5 max-w-2xl text-[16px] leading-relaxed text-muted md:text-[17px]">
      {children}
    </p>
  );
}

export function CheckIcon({ className = "" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 20 20"
      fill="none"
      className={className}
      aria-hidden="true"
    >
      <path
        d="M4.5 10.5l3.5 3.5 7.5-8"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function DotIcon({ className = "" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 20 20"
      fill="none"
      className={className}
      aria-hidden="true"
    >
      <circle cx="10" cy="10" r="3" fill="currentColor" />
    </svg>
  );
}

export function ArrowIcon({ className = "" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 20 20"
      fill="none"
      className={className}
      aria-hidden="true"
    >
      <path
        d="M4 10h11m0 0l-4.5-4.5M15 10l-4.5 4.5"
        stroke="currentColor"
        strokeWidth="1.6"
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
  // director
  "M4 6.5h16M4 6.5A1.5 1.5 0 015.5 5h13A1.5 1.5 0 0120 6.5M4 6.5v11A1.5 1.5 0 005.5 19h13a1.5 1.5 0 001.5-1.5v-11M9 5v14M15 5v14",
  // planner
  "M4 5h16v14H4V5zm0 5h16M9 10v9",
  // budget
  "M12 4v16M8.5 8.5A3 3 0 0111.5 6h1a3 3 0 010 6h-1a3 3 0 000 6h1a3 3 0 003-2.5",
  // reuse
  "M4.5 9.5A7.5 7.5 0 0117 6m2.5 8.5A7.5 7.5 0 017 18M4.5 5v4.5H9M19.5 19v-4.5H15",
  // voice
  "M12 4a3 3 0 013 3v5a3 3 0 01-6 0V7a3 3 0 013-3zM6 11.5a6 6 0 0012 0M12 17.5V21",
  // edit
  "M4 7h16M4 12h10M4 17h16M17.5 12l2.5 2.5-2.5 2.5",
  // providers
  "M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3zm0 0v18m8-13.5L12 12 4 7.5",
  // resilience
  "M12 3l7.5 3v6c0 4.5-3 7.5-7.5 9-4.5-1.5-7.5-4.5-7.5-9V6L12 3zm-3 9l2 2 4-4",
];

export function FeatureIcon({
  d,
  className = "",
}: {
  d: string;
  className?: string;
}) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden="true">
      <path
        d={d}
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
