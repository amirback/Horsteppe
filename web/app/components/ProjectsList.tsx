"use client";

import { useCallback, useState } from "react";
import Link from "next/link";
import type { Lang } from "../lib/i18n";
import { studio } from "../lib/studio-content";
import { usePolling, type PollOutcome } from "../lib/use-polling";
import { progressText } from "../lib/worker-text";
import { seconds, when } from "../lib/format";
import { Nav } from "./Nav";
import { Ambience } from "./Ambience";
import { Footer } from "./Footer";
import { ArrowIcon } from "./ui";
import { motion, Stagger, StaggerItem } from "./motion";

type Project = {
  id: string;
  topic: string;
  style: string;
  duration_sec: number;
  aspect_ratio: string | null;
  status: "queued" | "generating" | "done" | "done_degraded" | "failed";
  status_detail: string | null;
  created_at: string;
};

type Data = {
  projects: Project[];
  counts: { total: number; active: number; done: number; failed: number };
};

const POLL_MS = 5000;

/**
 * История проектов.
 *
 * Опрос идёт только пока что-то собирается: когда всё готово, страница
 * перестаёт дёргать сервер. Из-за отсутствия такой страницы было непонятно,
 * что именно висит в работе, когда лимит запрещал запускать новое.
 */
export function ProjectsList({ lang, email }: { lang: Lang; email: string | null }) {
  const s = studio[lang];
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (): Promise<PollOutcome> => {
    try {
      const res = await fetch("/api/projects", { cache: "no-store" });
      if (!res.ok) {
        const body: { error?: string } = await res.json().catch(() => ({}));
        setError(s.errors[body.error ?? "unknown"] ?? s.errors.unknown);
        return res.status === 401 || res.status === 403 ? "stop" : "error";
      }
      const body: Data = await res.json();
      setData(body);
      setError(null);
      // Опрос нужен, только пока что-то собирается.
      return body.counts.active > 0 ? "continue" : "stop";
    } catch {
      setError(s.errors.network);
      return "error";
    }
  }, [s]);

  usePolling(load, POLL_MS);

  const counts = data?.counts;

  return (
    <>
      <Ambience />
      <Nav lang={lang} email={email} />

      <main className="container-x min-h-[70svh] pb-16 pt-28 md:pb-20 md:pt-36">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <h1 className="font-display text-[28px] font-bold tracking-[-0.025em] text-ink md:text-[38px]">
            {s.library.title}
          </h1>
          <Link
            href={`/${lang}#top`}
            className="nav-link inline-flex items-center gap-2 rounded-full bg-ink px-5 py-2.5 text-cream transition hover:bg-forest"
          >
            {s.submit}
          </Link>
        </div>

        {counts ? (
          <div className="mt-7 flex flex-wrap gap-2.5">
            <Stat label={s.library.active} value={counts.active} accent={counts.active > 0} />
            <Stat label={s.library.done} value={counts.done} />
            <Stat label={s.library.failed} value={counts.failed} />
            <Stat label={s.library.total} value={counts.total} />
          </div>
        ) : null}

        {error ? (
          <p role="alert" className="mt-8 rounded-2xl border border-ember/40 bg-white/60 px-5 py-4 text-[14.5px] text-ember">
            {error}
          </p>
        ) : null}

        {data && data.projects.length === 0 ? (
          <div className="mt-12 rounded-3xl border border-ink/12 bg-white/45 px-6 py-12 text-center">
            <p className="text-[15px] text-ink-soft/80">{s.library.empty}</p>
            <Link
              href={`/${lang}#top`}
              className="nav-link mt-5 inline-flex items-center gap-2 rounded-full bg-ink px-6 py-3 text-cream transition hover:bg-forest"
            >
              {s.library.emptyCta}
              <ArrowIcon className="h-4 w-4" />
            </Link>
          </div>
        ) : null}

        {data && data.projects.length > 0 ? (
          <Stagger className="mt-8 grid gap-3" gap={0.05}>
            {data.projects.map((p) => (
              <StaggerItem key={p.id} y={14}>
                <Link
                  href={`/${lang}/projects/${p.id}`}
                  className="group flex flex-col gap-3 rounded-2xl border border-ink/12 bg-white/45 p-5 transition-all duration-300 hover:-translate-y-0.5 hover:border-ink/25 hover:bg-white/70 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="min-w-0">
                    <div className="truncate text-[15px] font-medium text-ink">{p.topic}</div>
                    <div className="mt-1 text-[12.5px] text-ink-soft/60">
                      {when(p.created_at, lang)} · {seconds(p.duration_sec, lang)} · {p.aspect_ratio ?? "9:16"}
                    </div>
                  </div>

                  <div className="flex shrink-0 items-center gap-3">
                    <Badge
                      status={p.status}
                      label={s.library.statuses[p.status] ?? s.library.statuses.done}
                      detail={progressText(p.status_detail, lang)}
                    />
                    <ArrowIcon className="h-4 w-4 text-ink-soft/40 transition group-hover:translate-x-0.5 group-hover:text-ink" />
                  </div>
                </Link>
              </StaggerItem>
            ))}
          </Stagger>
        ) : null}

        {!data && !error ? <div className="mt-10 h-32 animate-pulse rounded-2xl bg-ink/5" /> : null}
      </main>

      <Footer lang={lang} />
    </>
  );
}

function Stat({ label, value, accent = false }: { label: string; value: number; accent?: boolean }) {
  return (
    <div
      className={[
        "rounded-2xl border px-4 py-3",
        accent ? "border-sage/50 bg-sage/12" : "border-ink/12 bg-white/45",
      ].join(" ")}
    >
      <div className={`font-display text-[20px] font-bold ${accent ? "text-forest" : "text-ink"}`}>{value}</div>
      <div className="nav-link mt-0.5 text-ink-soft/55">{label}</div>
    </div>
  );
}

function Badge({ status, label, detail }: { status: string; label: string; detail: string | null }) {
  const active = status === "queued" || status === "generating";
  const tone =
    status === "done" || status === "done_degraded"
      ? "border-sage/50 bg-sage/15 text-forest"
      : status === "failed"
        ? "border-ember/40 bg-ember/10 text-ember"
        : "border-ink/15 bg-white/70 text-ink-soft";

  return (
    <span className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-[12px] ${tone}`}>
      {active ? (
        <motion.span
          className="h-1.5 w-1.5 rounded-full bg-sage"
          animate={{ opacity: [1, 0.25, 1] }}
          transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
        />
      ) : null}
      {active && detail ? detail : label}
    </span>
  );
}
