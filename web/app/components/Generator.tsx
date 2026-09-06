"use client";

import { useMemo, useRef, useState } from "react";
import { CONTACT_EMAIL } from "../lib/content";
import type { Lang } from "../lib/i18n";
import { studio } from "../lib/studio-content";
import { ArrowIcon, CheckIcon } from "./ui";
import { Magnetic, motion } from "./motion";

const MAX_PROMPT = 600;

/**
 * Форма «промпт → ролик».
 *
 * Сегодня генерация запускается вручную: ключей провайдеров и живой базы ещё
 * нет, поэтому форма собирает бриф и отправляет его письмом одним нажатием.
 * Это не заглушка — так описан concierge-этап в docs/BIBLE.md, и человек
 * действительно получает ролик, просто пока не автоматически.
 *
 * Когда появятся ключи, меняется ровно одно место — `submit`: вместо сборки
 * письма он делает POST в API и уводит на страницу статуса проекта.
 */
export function Generator({ lang, variant = "hero" }: { lang: Lang; variant?: "hero" | "page" }) {
  const s = studio[lang];
  const [prompt, setPrompt] = useState("");
  const [style, setStyle] = useState(s.style.options[0].value);
  const [duration, setDuration] = useState(s.duration.options[1].value);
  const [format, setFormat] = useState(s.format.options[0].value);
  const [sent, setSent] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");
  const areaRef = useRef<HTMLTextAreaElement>(null);

  const label = (opts: { value: string; label: string }[], value: string) =>
    opts.find((o) => o.value === value)?.label ?? value;

  const brief = useMemo(() => {
    const settings = [
      `${s.style.label}: ${label(s.style.options, style)}`,
      `${s.duration.label}: ${label(s.duration.options, duration)}`,
      `${s.format.label}: ${label(s.format.options, format)}`,
    ].join("\n");
    return `${s.brief.prompt}:\n${prompt.trim()}\n\n${s.brief.settings}:\n${settings}`;
  }, [prompt, style, duration, format, s]);

  const mailto = `mailto:${CONTACT_EMAIL}?${new URLSearchParams({
    subject: `Horsteppe — ${prompt.trim().slice(0, 60)}`,
    body: brief,
  }).toString()}`;

  const submit = () => {
    if (prompt.trim().length < 8) {
      setError(s.empty);
      areaRef.current?.focus();
      return;
    }
    setError("");
    setSent(true);
  };

  if (sent) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className="mx-auto w-full max-w-[680px] rounded-[28px] border-[1.5px] border-ink/20 bg-paper/85 p-6 text-left backdrop-blur-md md:p-8"
      >
        <h3 className="font-display text-[20px] font-bold text-ink md:text-[24px]">
          {s.brief.title}
        </h3>
        <p className="mt-2 text-[14.5px] leading-relaxed text-ink-soft/85">{s.brief.lead}</p>

        <pre className="mt-5 max-h-52 overflow-auto whitespace-pre-wrap rounded-2xl border border-ink/12 bg-white/60 p-4 font-sans text-[13.5px] leading-relaxed text-ink-soft">
          {brief}
        </pre>

        <div className="mt-5 flex flex-wrap items-center gap-2.5">
          <Magnetic strength={0.18}>
            <a
              href={mailto}
              className="nav-link inline-flex items-center gap-2 rounded-full bg-ink px-6 py-3 text-cream transition hover:bg-forest"
            >
              {s.brief.send}
              <ArrowIcon className="h-4 w-4" />
            </a>
          </Magnetic>
          <button
            type="button"
            onClick={async () => {
              try {
                await navigator.clipboard.writeText(brief);
                setCopied(true);
                window.setTimeout(() => setCopied(false), 2000);
              } catch {
                /* буфер недоступен — текст всё равно виден и его можно выделить */
              }
            }}
            className="nav-link inline-flex items-center gap-2 rounded-full border-[1.5px] border-ink/25 px-5 py-3 text-ink-soft transition hover:border-ink hover:text-ink"
          >
            {copied ? <CheckIcon className="h-4 w-4" /> : null}
            {copied ? s.brief.copied : s.brief.copy}
          </button>
          <button
            type="button"
            onClick={() => setSent(false)}
            className="nav-link px-3 py-3 text-ink-soft/60 transition hover:text-ink"
          >
            {s.brief.back}
          </button>
        </div>

        <ol className="mt-7 space-y-2.5 border-t border-ink/10 pt-5">
          {s.brief.steps.map((step, i) => (
            <li key={step} className="flex items-start gap-3">
              <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-ink/8 text-[11px] font-semibold text-ink-soft/70">
                {i + 1}
              </span>
              <span className="text-[14px] leading-snug text-ink-soft/85">{step}</span>
            </li>
          ))}
        </ol>
      </motion.div>
    );
  }

  return (
    <div className={`mx-auto w-full ${variant === "hero" ? "max-w-[680px]" : "max-w-[760px]"}`}>
      <div className="rounded-[28px] border-[1.5px] border-ink/25 bg-paper/70 p-2.5 backdrop-blur-md transition-colors focus-within:border-ink">
        <div className="flex flex-col items-stretch gap-2 sm:flex-row sm:items-end">
          <textarea
            ref={areaRef}
            value={prompt}
            maxLength={MAX_PROMPT}
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
            className="min-h-[54px] w-full flex-1 resize-none bg-transparent px-4 py-3 text-[15.5px] leading-snug text-ink outline-none placeholder:text-ink-soft/45"
          />
          <Magnetic strength={0.16} className="w-full sm:w-auto">
            <button
              type="button"
              onClick={submit}
              className="nav-link mb-0.5 inline-flex w-full shrink-0 items-center justify-center gap-2 whitespace-nowrap rounded-full bg-ink px-6 py-3.5 text-cream transition hover:bg-forest sm:w-auto"
            >
              {s.submit}
              <ArrowIcon className="h-4 w-4" />
            </button>
          </Magnetic>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center justify-center gap-2">
        <Select label={s.style.label} options={s.style.options} value={style} onChange={setStyle} />
        <Select label={s.duration.label} options={s.duration.options} value={duration} onChange={setDuration} />
        <Select label={s.format.label} options={s.format.options} value={format} onChange={setFormat} />
      </div>

      {error ? (
        <p className="mt-3 text-center text-[13px] text-ember">{error}</p>
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
              onClick={() => {
                setPrompt(ex);
                setError("");
                areaRef.current?.focus();
              }}
              className="max-w-full truncate rounded-full border border-ink/15 bg-paper/70 px-4 py-2 backdrop-blur-sm text-[12.5px] text-ink-soft/80 transition hover:border-ink/35 hover:bg-white/70 hover:text-ink"
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
}: {
  label: string;
  options: { value: string; label: string }[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="relative inline-flex items-center rounded-full border border-ink/20 bg-white/50 pl-4 pr-9 transition hover:border-ink/40">
      <span className="sr-only">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="cursor-pointer appearance-none bg-transparent py-2 text-[12.5px] text-ink-soft outline-none"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      <svg
        viewBox="0 0 20 20"
        fill="none"
        aria-hidden="true"
        className="pointer-events-none absolute right-3.5 h-3.5 w-3.5 text-ink-soft/50"
      >
        <path d="M5 8l5 5 5-5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </label>
  );
}
