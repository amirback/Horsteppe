"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";

type Scene = {
  order_index: number;
  narration: string;
  status: string;
  image_url: string | null;
};

type ProjectData = {
  project: {
    id: string;
    topic: string;
    style: string;
    duration_sec: number;
    status: "queued" | "generating" | "done" | "failed";
    status_detail: string | null;
    error_message: string | null;
  };
  scenes: Scene[];
  render: { final_video_url: string; duration_sec: number | null } | null;
};

const SCENE_STEPS: Record<string, number> = {
  pending: 0,
  audio_done: 1,
  image_done: 2,
  video_done: 3,
  failed: 0,
};

export function ProjectStatus({ projectId }: { projectId: string }) {
  const [data, setData] = useState<ProjectData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await fetch(`/api/projects/${projectId}`, { cache: "no-store" });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setError(body.error ?? `Ошибка ${res.status}`);
        return null;
      }
      const body: ProjectData = await res.json();
      setData(body);
      setError(null);
      return body;
    } catch {
      return null;
    }
  }, [projectId]);

  useEffect(() => {
    let stopped = false;

    async function tick() {
      const body = await load();
      if (stopped) return;
      const status = body?.project.status;
      if (status === "done" || status === "failed") return;
      timerRef.current = setTimeout(tick, 3000);
    }

    tick();
    return () => {
      stopped = true;
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [load]);

  if (error) {
    return (
      <div className="space-y-4 pt-10 text-center">
        <p className="text-neutral-400">{error}</p>
        <Link href="/projects" className="font-medium text-white hover:underline">
          ← К списку видео
        </Link>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex justify-center py-24">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-white/20 border-t-white" />
      </div>
    );
  }

  const { project, scenes, render } = data;
  const inProgress = project.status === "queued" || project.status === "generating";
  const progress = computeProgress(project.status, scenes);

  return (
    <div className="space-y-10">
      <div>
        <Link href="/projects" className="text-sm text-neutral-500 transition-colors hover:text-white">
          ← Мои видео
        </Link>
        <h1 className="mt-3 break-words text-xl font-semibold leading-snug tracking-tight sm:text-2xl">
          {project.topic}
        </h1>
        <p className="mt-2 text-sm text-neutral-400">
          {project.style} · {project.duration_sec} сек
        </p>
      </div>

      {inProgress && (
        <div className="card space-y-4 p-5 sm:p-8">
          <div className="flex items-center gap-3">
            <span className="relative flex h-2.5 w-2.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-violet-400 opacity-60" />
              <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-violet-400" />
            </span>
            <span className="text-sm font-medium text-neutral-200">
              {project.status_detail ?? "Генерация…"}
            </span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
            <div
              className="h-full rounded-full bg-gradient-to-r from-violet-500 to-fuchsia-500 transition-all duration-700"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-xs text-neutral-500">
            Обычно занимает несколько минут. Страницу можно закрыть — видео появится в «Моих видео».
          </p>
        </div>
      )}

      {project.status === "failed" && (
        <div className="card !border-red-500/30 !bg-red-500/10 p-5 sm:p-8">
          <p className="font-medium text-red-400">Не получилось</p>
          <p className="mt-1 text-sm text-red-400/80">
            {project.error_message ?? "Неизвестная ошибка"}
          </p>
        </div>
      )}

      {project.status === "done" && render && (
        <div className="space-y-5">
          <video
            src={render.final_video_url}
            controls
            playsInline
            className="mx-auto aspect-[9/16] w-full max-w-xs rounded-2xl border border-white/10 bg-black"
          />
          <div className="text-center">
            <a href={render.final_video_url} download className="btn-primary">
              Скачать mp4
            </a>
          </div>
        </div>
      )}

      {scenes.length > 0 && (
        <div className="space-y-4">
          <h2 className="label">Сцены</h2>
          <ol className="space-y-3">
            {scenes.map((s) => (
              <li key={s.order_index} className="card flex items-start gap-4 p-4">
                {s.image_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={s.image_url}
                    alt=""
                    className="h-20 w-12 shrink-0 rounded-lg border border-white/10 object-cover"
                  />
                ) : (
                  <div className="flex h-20 w-12 shrink-0 items-center justify-center rounded-lg bg-white/5 text-xs font-medium text-neutral-500">
                    {s.order_index + 1}
                  </div>
                )}
                <p className="text-sm leading-relaxed text-neutral-400">{s.narration}</p>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}

function computeProgress(status: string, scenes: Scene[]): number {
  if (status === "done") return 100;
  if (!scenes.length) return 8;
  const maxSteps = scenes.length * 3;
  const doneSteps = scenes.reduce((acc, s) => acc + (SCENE_STEPS[s.status] ?? 0), 0);
  return Math.min(95, 10 + Math.round((doneSteps / maxSteps) * 80));
}
