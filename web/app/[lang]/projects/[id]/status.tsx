"use client";

import { useCallback, useState } from "react";
import Link from "next/link";
import type { Lang } from "../../../lib/i18n";
import { studio } from "../../../lib/studio-content";
import { usePolling, type PollOutcome } from "../../../lib/use-polling";
import { degradedText, failureText, progressText } from "../../../lib/worker-text";
import { seconds } from "../../../lib/format";
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
    status: "queued" | "generating" | "done" | "done_degraded" | "failed";
    status_detail: string | null;
    error_message: string | null;
    /** Доля таймлайна, закрытая настоящим AI-видео. Зум по фотографии сюда не входит. */
    real_video_coverage: number | null;
    /** Почему ролик готов, но ниже цели. Показывается рядом с плеером. */
    degraded_reason: string | null;
  };
  scenes: Scene[];
  render: { final_video_url: string; duration_sec: number | null } | null;
};

const POLL_MS = 3000;

function isFinal(status: Data["project"]["status"]): boolean {
  return status === "done" || status === "done_degraded" || status === "failed";
}

/**
 * Ссылка, по которой файл именно скачивается, а не открывается.
 *
 * Атрибут `download` работает только для адресов того же сайта. Ролик
 * лежит в хранилище на другом домене, и кнопка «Скачать» открывала видео
 * во вкладке — на телефоне это ещё и полноэкранный плеер без выхода назад.
 * Хранилище Supabase понимает параметр `download` и само отдаёт файл как
 * вложение с нужным именем.
 */
function downloadUrl(url: string, projectId: string): string {
  const name = `horsteppe-${projectId.slice(0, 8)}.mp4`;
  return `${url}${url.includes("?") ? "&" : "?"}download=${encodeURIComponent(name)}`;
}


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
  email?: string | null;
}) {
  const s = studio[lang];
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (): Promise<PollOutcome> => {
    try {
      const res = await fetch(`/api/projects/${projectId}`, { cache: "no-store" });
      if (!res.ok) {
        const body: { error?: string } = await res.json().catch(() => ({}));
        setError(s.errors[body.error ?? "unknown"] ?? s.errors.unknown);
        // Проекта нет, он чужой или сессия истекла — повтор этого не
        // исправит. Раньше страница спрашивала об этом каждые три секунды
        // вечно.
        return res.status === 401 || res.status === 403 || res.status === 404 ? "stop" : "error";
      }
      const body: Data = await res.json();
      setData(body);
      setError(null);
      return isFinal(body.project.status) ? "stop" : "continue";
    } catch {
      setError(s.errors.network);
      return "error";
    }
  }, [projectId, s]);

  const restartPolling = usePolling(load, POLL_MS);

  const [retrying, setRetrying] = useState(false);
  const [retryError, setRetryError] = useState<string | null>(null);

  /** Ставит упавший проект обратно в очередь и возобновляет опрос состояния. */
  const retry = useCallback(async () => {
    if (retrying) return;
    setRetrying(true);
    setRetryError(null);
    try {
      const res = await fetch(`/api/projects/${projectId}/retry`, { method: "POST" });
      if (!res.ok) {
        const body: { error?: string } = await res.json().catch(() => ({}));
        setRetryError(s.errors[body.error ?? "unknown"] ?? s.errors.unknown);
        return;
      }
      // Опрос остановился, когда проект упал, — будим его.
      restartPolling();
    } catch {
      setRetryError(s.errors.network);
    } finally {
      setRetrying(false);
    }
  }, [projectId, s, retrying, restartPolling]);

  const project = data?.project;
  const render = data?.render;
  // Ролик с оговоркой — это готовый ролик: он играется и скачивается.
  // Разница только в том, что о невыполненном обещании сказано вслух.
  const degraded = project?.status === "done_degraded";
  const done = (project?.status === "done" || degraded) && render;
  const failed = project?.status === "failed";
  const coverage = project?.real_video_coverage;
  const degradedNote = degradedText(project?.degraded_reason, lang);
  const failureNote = retryError ?? failureText(project?.error_message, lang) ?? s.errors.unknown;

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

            {done && degradedNote ? (
              <p className="mt-4 max-w-2xl rounded-2xl border border-ink/15 bg-white/60 px-4 py-3 text-[13.5px] leading-relaxed text-ink-soft/85">
                {degradedNote}
              </p>
            ) : null}

            {done && coverage !== null && coverage !== undefined ? (
              <p className="mt-2 text-[12.5px] text-ink-soft/70">
                {s.project.realMotion}: {Math.round(coverage * 100)}%
              </p>
            ) : null}

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
                    href={downloadUrl(render!.final_video_url, project.id)}
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
                      {s.project.duration}: {seconds(render!.duration_sec, lang)}
                    </span>
                  ) : null}
                </div>
              </motion.div>
            ) : failed ? (
              <div className="mt-8 max-w-2xl rounded-2xl border border-ember/40 bg-white/60 px-5 py-4">
                <p className="text-[14.5px] leading-relaxed text-ember">
                  {failureNote}
                </p>
                <div className="mt-4 flex flex-wrap items-center gap-3">
                  <button
                    type="button"
                    onClick={retry}
                    disabled={retrying}
                    className="nav-link inline-flex items-center gap-2 rounded-full bg-ink px-5 py-3 text-cream transition hover:bg-forest disabled:opacity-70"
                  >
                    {retrying ? s.project.queued : s.project.retry}
                  </button>
                  <Link
                    href={`/${lang}`}
                    className="nav-link inline-flex items-center gap-2 rounded-full border-[1.5px] border-ink/25 px-5 py-3 text-ink-soft transition hover:border-ink hover:text-ink"
                  >
                    {s.project.again}
                  </Link>
                </div>
              </div>
            ) : (
              <Progress
                detail={progressText(project.status_detail, lang)}
                scenes={data!.scenes}
                stages={s.project.stages}
                scenesLabel={s.project.scenes}
              />
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
