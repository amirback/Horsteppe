"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type { Lang } from "../lib/i18n";
import { studio } from "../lib/studio-content";
import { ArrowIcon } from "./ui";
import { Magnetic, motion } from "./motion";

const MAX_PROMPT = 500;
const MIN_PROMPT = 8;

/**
 * Форма «промпт → ролик».
 *
 * Отправляет задачу в настоящий backend и уводит на страницу проекта, где
 * видно реальное состояние сборки. Никакой почты: ТЗ прямо запрещает
 * email-поток как способ создания видео.
 */
export function Generator({ lang, variant = "hero" }: { lang: Lang; variant?: "hero" | "page" }) {
  const s = studio[lang];
  const router = useRouter();
  const [prompt, setPrompt] = useState("");
  const [style, setStyle] = useState(s.style.options[0].value);
  const [duration, setDuration] = useState(s.duration.options[1].value);
  const [format, setFormat] = useState(s.format.options[0].value);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const areaRef = useRef<HTMLTextAreaElement>(null);

  const message = (code: string) => s.errors[code] ?? s.errors.unknown;

  async function submit() {
    if (prompt.trim().length < MIN_PROMPT) {
      setError(s.empty);
      areaRef.current?.focus();
      return;
    }
    setError("");
    setBusy(true);
    try {
      const res = await fetch("/api/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topic: prompt.trim(),
          style,
          duration_sec: Number(duration),
          aspect_ratio: format,
        }),
      });

      if (res.status === 401) {
        router.push(`/${lang}/login?next=${encodeURIComponent(`/${lang}`)}`);
        return;
      }

      const data: { id?: string; error?: string } = await res.json().catch(() => ({}));

      if (!res.ok) {
        setError(message(data.error ?? "unknown"));
        return;
      }
      router.push(`/${lang}/projects/${data.id}`);
    } catch {
      setError(message("network"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={`mx-auto w-full ${variant === "hero" ? "max-w-[680px]" : "max-w-[760px]"}`}>
      <div className="rounded-[28px] border-[1.5px] border-ink/25 bg-paper/70 p-2.5 backdrop-blur-md transition-colors focus-within:border-ink">
        <div className="flex flex-col items-stretch gap-2 sm:flex-row sm:items-end">
          <textarea
            ref={areaRef}
            value={prompt}
            maxLength={MAX_PROMPT}
            disabled={busy}
            onChange={(e) => {
              setPrompt(e.target.value);
              if (error) setError("");
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submit();
            }}
            rows={variant === "hero" ? 2 : 3}
            placeholder={s.placeholder}
            aria-label={s.placeholder}
            className="min-h-[54px] w-full flex-1 resize-none bg-transparent px-4 py-3 text-[15.5px] leading-snug text-ink outline-none placeholder:text-ink-soft/45 disabled:opacity-60"
          />
          <Magnetic strength={0.16} className="w-full sm:w-auto">
            <button
              type="button"
              onClick={submit}
              disabled={busy}
              className="nav-link mb-0.5 inline-flex w-full shrink-0 items-center justify-center gap-2 whitespace-nowrap rounded-full bg-ink px-6 py-3.5 text-cream transition hover:bg-forest disabled:opacity-70 sm:w-auto"
            >
              {busy ? s.working : s.submit}
              {busy ? null : <ArrowIcon className="h-4 w-4" />}
            </button>
          </Magnetic>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center justify-center gap-2">
        <Select label={s.style.label} options={s.style.options} value={style} onChange={setStyle} disabled={busy} />
        <Select label={s.duration.label} options={s.duration.options} value={duration} onChange={setDuration} disabled={busy} />
        <Select label={s.format.label} options={s.format.options} value={format} onChange={setFormat} disabled={busy} />
      </div>

      {error ? (
        <motion.p
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          role="alert"
          className="mx-auto mt-4 max-w-[560px] rounded-2xl border border-ember/40 bg-paper/80 px-4 py-2.5 text-center text-[13px] leading-relaxed text-ember backdrop-blur-sm"
        >
          {error}
        </motion.p>
      ) : (
        <p className="mx-auto mt-4 max-w-[560px] rounded-2xl bg-paper/55 px-4 py-2.5 text-center text-[12.5px] leading-relaxed text-ink-soft/80 backdrop-blur-sm">
          {s.notice}
        </p>
      )}

      <div className="mt-5">
        <div className="text-center text-[11.5px] uppercase tracking-[0.14em] text-ink-soft/60 [text-shadow:0_1px_10px_rgba(247,246,233,0.85)]">
          {s.examplesLabel}
        </div>
        <div className="mt-3 flex flex-wrap justify-center gap-2">
          {s.examples.map((ex) => (
            <button
              key={ex}
              type="button"
              disabled={busy}
              onClick={() => {
                setPrompt(ex);
                setError("");
                areaRef.current?.focus();
              }}
              className="max-w-full truncate rounded-full border border-ink/15 bg-paper/70 px-4 py-2 text-[12.5px] text-ink-soft/80 backdrop-blur-sm transition hover:border-ink/35 hover:bg-white/70 hover:text-ink disabled:opacity-60"
            >
              {ex}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function Select({
  label,
  options,
  value,
  onChange,
  disabled,
}: {
  label: string;
  options: { value: string; label: string }[];
  value: string;
  onChange: (v: string) => void;
  disabled?: boolean;
}) {
  return (
    <label className="relative inline-flex items-center rounded-full border border-ink/20 bg-white/50 pl-4 pr-9 transition hover:border-ink/40">
      <span className="sr-only">{label}</span>
      <select
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        className="cursor-pointer appearance-none bg-transparent py-2 text-[12.5px] text-ink-soft outline-none disabled:opacity-60"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      <svg viewBox="0 0 20 20" fill="none" aria-hidden="true" className="pointer-events-none absolute right-3.5 h-3.5 w-3.5 text-ink-soft/50">
        <path d="M5 8l5 5 5-5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </label>
  );
}
