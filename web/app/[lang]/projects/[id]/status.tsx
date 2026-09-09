"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import type { Lang } from "../../../lib/i18n";
import { studio } from "../../../lib/studio-content";
import { ArrowIcon, CheckIcon } from "../../../components/ui";
import { motion } from "../../../components/motion";
import { Nav } from "../../../components/Nav";
import { Ambience } from "../../../components/Ambience";
import { Footer } from "../../../components/Footer";

type Scene = {
  order_index: number;
  narration: string;
  status: string;
  image_url: string | null;
};

type Data = {
  project: {
    id: string;
    topic: string;
    style: string;
    duration_sec: number;
    aspect_ratio: string | null;
    status: "queued" | "generating" | "done" | "failed";
    status_detail: string | null;
    error_message: string | null;
  };
  scenes: Scene[];
  render: { final_video_url: string; duration_sec: number | null } | null;
};

const POLL_MS = 3000;

/**
 * Страница проекта.
 *
 * Прогресс берётся из базы, а не рисуется таймером: ТЗ прямо запрещает
 * показывать выдуманный прогресс. Опрос прекращается, как только состояние
 * стало окончательным.
 */
export function ProjectStatus({
  lang,
  projectId,
  email,
}: {
  lang: Lang;
  projectId: string;
  email: string | null;
}) {
  const s = studio[lang];
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = useCallback(async (): Promise<Data | null> => {
    try {
      const res = await fetch(`/api/projects/${projectId}`, { cache: "no-store" });
      if (!res.ok) {
        const body: { error?: string } = await res.json().catch(() => ({}));
        setError(s.errors[body.error ?? "unknown"] ?? s.errors.unknown);
        return null;
      }
      const body: Data = await res.json();
      setData(body);
      setError(null);
      return body;
    } catch {
      setError(s.errors.network);
      return null;
    }
  }, [projectId, s]);

  useEffect(() => {
    let stopped = false;
    async function tick() {
      const body = await load();
      if (stopped) return;
      const status = body?.project.status;
      if (status === "done" || status === "failed") return;
      timer.current = setTimeout(tick, POLL_MS);
    }
    tick();
    return () => {
      stopped = true;
      if (timer.current) clearTimeout(timer.current);
    };
  }, [load]);

  const project = data?.project;
  const render = data?.render;
  const done = project?.status === "done" && render;
  const failed = project?.status === "failed";

  return (
    <>
      <Ambience />
      <Nav lang={lang} email={email} />

      <main className="container-x min-h-[70svh] pb-16 pt-28 md:pb-20 md:pt-36">
        {error && !project ? (
          <p role="alert" className="rounded-2xl border border-ember/40 bg-white/60 px-5 py-4 text-[14.5px] text-ember">
            {error}
          </p>
        ) : null}

        {project ? (
          <>
            <h1 className="font-display max-w-3xl text-balance text-[26px] font-bold leading-tight tracking-[-0.02em] text-ink md:text-[36px]">
              {done ? s.project.ready : failed ? s.project.failed : s.project.working}
            </h1>
            <p className="mt-3 max-w-2xl text-[15px] leading-relaxed text-ink-soft/80">
              {project.topic}
            </p>

            {done ? (
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
                className="mt-9"
              >
                <div className="overflow-hidden rounded-[28px] border border-ink/12 bg-black">
                  <video
                    src={render!.final_video_url}
                    controls
                    playsInline
                    preload="metadata"
                    className="mx-auto max-h-[70vh] w-auto"
                  />
                </div>
                <div className="mt-6 flex flex-wrap items-center gap-3">
                  <a
                    href={render!.final_video_url}
                    download
                    className="nav-link inline-flex items-center gap-2 rounded-full bg-ink px-6 py-3.5 text-cream transition hover:bg-forest"
                  >
                    {s.project.download}
                    <ArrowIcon className="h-4 w-4" />
                  </a>
                  <Link
                    href={`/${lang}`}
                    className="nav-link inline-flex items-center gap-2 rounded-full border-[1.5px] border-ink/25 px-6 py-3.5 text-ink-soft transition hover:border-ink hover:text-ink"
                  >
                    {s.project.again}
                  </Link>
                  {render!.duration_sec ? (
                    <span className="text-[13px] text-ink-soft/60">
                      {s.project.duration}: {Math.round(render!.duration_sec)} s
                    </span>
                  ) : null}
                </div>
              </motion.div>
            ) : failed ? (
              <div className="mt-8 max-w-2xl rounded-2xl border border-ember/40 bg-white/60 px-5 py-4">
                <p className="text-[14.5px] leading-relaxed text-ember">
                  {project.error_message ?? s.errors.unknown}
                </p>
                <Link
                  href={`/${lang}`}
                  className="nav-link mt-4 inline-flex items-center gap-2 rounded-full bg-ink px-5 py-3 text-cream transition hover:bg-forest"
                >
                  {s.project.retry}
                </Link>
              </div>
            ) : (
              <Progress detail={project.status_detail} scenes={data!.scenes} stages={s.project.stages} scenesLabel={s.project.scenes} />
            )}
          </>
        ) : !error ? (
          <div className="h-40 animate-pulse rounded-2xl bg-ink/5" />
        ) : null}
      </main>

      <Footer lang={lang} />
    </>
  );
}

/** Живое состояние: строка из базы плюс готовность каждой сцены. */
function Progress({
  detail,
  scenes,
  stages,
  scenesLabel,
}: {
  detail: string | null;
  scenes: Scene[];
  stages: string[];
  scenesLabel: string;
}) {
  const ready = scenes.filter((x) => x.status !== "pending" && x.status !== "failed").length;

  return (
    <div className="mt-9 max-w-2xl">
      <div className="flex items-center gap-3 rounded-2xl border border-ink/12 bg-white/55 px-5 py-4">
        <span className="relative flex h-2.5 w-2.5 shrink-0">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-sage opacity-70" />
          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-sage" />
        </span>
        <span className="text-[15px] text-ink">{detail ?? stages[0]}</span>
      </div>

      {scenes.length ? (
        <div className="mt-6">
          <div className="nav-link text-ink-soft/55">
            {scenesLabel}: {ready} / {scenes.length}
          </div>
          <ul className="mt-3 space-y-2">
            {scenes.map((scene) => {
              const isReady = scene.status !== "pending" && scene.status !== "failed";
              return (
                <li key={scene.order_index} className="flex items-start gap-3">
                  <span
                    className={[
                      "mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border transition-colors",
                      isReady ? "border-sage bg-sage/15 text-sage" : "border-ink/20 text-ink-soft/40",
                    ].join(" ")}
                  >
                    {isReady ? <CheckIcon className="h-3.5 w-3.5" /> : null}
                  </span>
                  <span className="text-[14px] leading-snug text-ink-soft/85">{scene.narration}</span>
                </li>
              );
            })}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
