"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type { Lang } from "../lib/i18n";
import { studio } from "../lib/studio-content";
import { productStudio } from "../lib/product-content";
import { ArrowIcon } from "./ui";
import { Magnetic, motion } from "./motion";

const MAX_PROMPT = 500;
const MIN_PROMPT = 8;
const MAX_PHOTOS = 5;

type Mode = "general_video" | "product_ad" | "image_to_video";
type Picked = { file: File; preview: string };

/**
 * Форма «промпт → ролик».
 *
 * Отправляет задачу в настоящий backend и уводит на страницу проекта, где
 * видно реальное состояние сборки. Никакой почты: ТЗ прямо запрещает
 * email-поток как способ создания видео.
 */
export function Generator({ lang, variant = "hero" }: { lang: Lang; variant?: "hero" | "page" }) {
  const s = studio[lang];
  const p = productStudio[lang];
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("general_video");
  const [prompt, setPrompt] = useState("");
  const [photos, setPhotos] = useState<Picked[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [benefits, setBenefits] = useState("");
  const [audience, setAudience] = useState("");
  const [cta, setCta] = useState("");
  const [goal, setGoal] = useState("sales");
  const [budget, setBudget] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const [style, setStyle] = useState(s.style.options[0].value);
  const [duration, setDuration] = useState(s.duration.options[1].value);
  const [format, setFormat] = useState(s.format.options[0].value);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const areaRef = useRef<HTMLTextAreaElement>(null);

  const message = (code: string) => p.errors[code] ?? s.errors[code] ?? s.errors.unknown;

  // Превью живут в памяти браузера: без освобождения каждая замена фотографии
  // оставляла бы за собой мегабайты.
  useEffect(() => () => photos.forEach((item) => URL.revokeObjectURL(item.preview)), [photos]);

  function addPhotos(list: FileList | null) {
    if (!list) return;
    const room = MAX_PHOTOS - photos.length;
    if (room <= 0) {
      setError(message("too_many_files"));
      return;
    }
    const picked = Array.from(list)
      .slice(0, room)
      .map((file) => ({ file, preview: URL.createObjectURL(file) }));
    setPhotos((current) => [...current, ...picked]);
    setError("");
    if (fileRef.current) fileRef.current.value = "";
  }

  function removePhoto(index: number) {
    setPhotos((current) => {
      URL.revokeObjectURL(current[index].preview);
      return current.filter((_, i) => i !== index);
    });
  }

  /** Тема проекта. У рекламы её собирает форма, у остальных пишет человек. */
  function topicFor(): string {
    if (mode !== "product_ad") return prompt.trim();
    return [name.trim(), description.trim()].filter(Boolean).join(". ");
  }

  async function submit() {
    // Проверки на клиенте — вежливость, а не защита: сервер проверяет всё
    // заново. Смысл в том, чтобы человек узнал о пропущенном поле сразу.
    if (mode === "product_ad" && !name.trim()) {
      setError(message("product_name_required"));
      return;
    }
    if (mode === "image_to_video" && photos.length === 0) {
      setError(message("photo_required"));
      return;
    }
    if (mode !== "product_ad" && prompt.trim().length < MIN_PROMPT) {
      setError(s.empty);
      areaRef.current?.focus();
      return;
    }
    setError("");
    setBusy(true);
    try {
      let references: unknown[] = [];
      if (photos.length > 0) {
        setUploading(true);
        const form = new FormData();
        photos.forEach((item) => form.append("files", item.file));
        const upload = await fetch("/api/uploads", { method: "POST", body: form });
        const uploaded: { items?: unknown[]; error?: string } = await upload
          .json()
          .catch(() => ({}));
        setUploading(false);
        if (upload.status === 401) {
          router.push(`/${lang}/login?next=${encodeURIComponent(`/${lang}`)}`);
          return;
        }
        if (!upload.ok) {
          setError(message(uploaded.error ?? "upload_failed"));
          return;
        }
        references = uploaded.items ?? [];
      }

      const res = await fetch("/api/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topic: topicFor(),
          style,
          duration_sec: Number(duration),
          aspect_ratio: format,
          project_type: mode,
          references,
          max_budget_usd: budget.trim() === "" ? null : Number(budget),
          brief:
            mode === "product_ad"
              ? {
                  product_name: name.trim(),
                  product_description: description.trim(),
                  product_benefits: benefits
                    .split(/[;\n]/)
                    .map((b) => b.trim())
                    .filter(Boolean),
                  target_audience: audience.trim(),
                  ad_goal: goal,
                  call_to_action: cta.trim(),
                }
              : {},
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
      setUploading(false);
    }
  }

  const modes: { value: Mode; label: string }[] = [
    { value: "general_video", label: p.modes.video },
    { value: "product_ad", label: p.modes.ad },
    { value: "image_to_video", label: p.modes.animate },
  ];
  const submitLabel =
    mode === "product_ad" ? p.submitAd : mode === "image_to_video" ? p.submitAnimate : s.submit;

  return (
    <div className={`mx-auto w-full ${variant === "hero" ? "max-w-[680px]" : "max-w-[760px]"}`}>
      <div className="mb-3 flex flex-wrap justify-center gap-1.5">
        {modes.map((item) => (
          <button
            key={item.value}
            type="button"
            disabled={busy}
            onClick={() => {
              setMode(item.value);
              setError("");
            }}
            aria-pressed={mode === item.value}
            className={`rounded-full px-4 py-2 text-[12.5px] transition disabled:opacity-60 ${
              mode === item.value
                ? "bg-ink text-cream"
                : "border border-ink/15 bg-paper/70 text-ink-soft/80 backdrop-blur-sm hover:border-ink/35 hover:text-ink"
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      {mode !== "general_video" ? (
        <div className="mb-3 rounded-[28px] border-[1.5px] border-ink/25 bg-paper/70 p-4 backdrop-blur-md">
          <div className="text-left text-[12.5px] text-ink-soft/80">{p.photos.label}</div>
          <p className="mt-1 text-left text-[11.5px] leading-relaxed text-ink-soft/60">{p.photos.hint}</p>

          <div className="mt-3 flex flex-wrap items-center gap-2">
            {photos.map((item, index) => (
              <div key={item.preview} className="relative">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={item.preview}
                  alt=""
                  className="h-20 w-16 rounded-xl border border-ink/15 object-cover"
                />
                {index === 0 ? (
                  <span className="absolute left-1 top-1 rounded-full bg-ink/85 px-1.5 py-0.5 text-[9px] uppercase tracking-wide text-cream">
                    {p.photos.primary}
                  </span>
                ) : null}
                <button
                  type="button"
                  onClick={() => removePhoto(index)}
                  disabled={busy}
                  aria-label={p.photos.remove}
                  className="absolute -right-1.5 -top-1.5 flex h-5 w-5 items-center justify-center rounded-full border border-ink/20 bg-paper text-[11px] text-ink-soft transition hover:text-ember"
                >
                  ×
                </button>
              </div>
            ))}

            {photos.length < MAX_PHOTOS ? (
              <button
                type="button"
                onClick={() => fileRef.current?.click()}
                disabled={busy}
                className="h-20 w-16 rounded-xl border border-dashed border-ink/30 text-[11px] leading-tight text-ink-soft/70 transition hover:border-ink/50 hover:text-ink disabled:opacity-60"
              >
                + {p.photos.add}
              </button>
            ) : null}
            <input
              ref={fileRef}
              type="file"
              multiple
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              onChange={(e) => addPhotos(e.target.files)}
            />
          </div>

          {mode === "product_ad" ? (
            <div className="mt-4 grid gap-2.5 text-left sm:grid-cols-2">
              <Field label={p.fields.name} value={name} onChange={setName} placeholder={p.fields.namePlaceholder} disabled={busy} />
              <Field label={p.fields.description} value={description} onChange={setDescription} placeholder={p.fields.descriptionPlaceholder} disabled={busy} />
              <Field label={p.fields.benefits} value={benefits} onChange={setBenefits} placeholder={p.fields.benefitsPlaceholder} disabled={busy} />
              <Field label={p.fields.audience} value={audience} onChange={setAudience} placeholder={p.fields.audiencePlaceholder} disabled={busy} />
              <Field label={p.fields.cta} value={cta} onChange={setCta} placeholder={p.fields.ctaPlaceholder} disabled={busy} />
              <label className="block">
                <span className="mb-1 block text-[11.5px] text-ink-soft/70">{p.fields.goal}</span>
                <select
                  value={goal}
                  disabled={busy}
                  onChange={(e) => setGoal(e.target.value)}
                  className="w-full rounded-xl border border-ink/15 bg-white/60 px-3 py-2 text-[13px] text-ink outline-none transition focus:border-ink/45 disabled:opacity-60"
                >
                  {p.fields.goalOptions.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          ) : null}

          <div className="mt-2.5 text-left">
            <Field
              label={p.fields.budget}
              value={budget}
              onChange={setBudget}
              placeholder="3"
              disabled={busy}
              inputMode="decimal"
            />
            <p className="mt-1 text-left text-[11px] leading-relaxed text-ink-soft/60">{p.fields.budgetHint}</p>
          </div>
        </div>
      ) : null}

      <div className="rounded-[28px] border-[1.5px] border-ink/25 bg-paper/70 p-2.5 backdrop-blur-md transition-colors focus-within:border-ink">
        <div
          className={`flex flex-col items-stretch gap-2 sm:flex-row sm:items-end ${
            mode === "product_ad" ? "sm:justify-center" : ""
          }`}
        >
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
            placeholder={mode === "image_to_video" ? p.animate.motionPlaceholder : s.placeholder}
            aria-label={mode === "image_to_video" ? p.animate.motion : s.placeholder}
            hidden={mode === "product_ad"}
            className="min-h-[54px] w-full flex-1 resize-none bg-transparent px-4 py-3 text-[15.5px] leading-snug text-ink outline-none placeholder:text-ink-soft/45 disabled:opacity-60"
          />
          <Magnetic strength={0.16} className="w-full sm:w-auto">
            <button
              type="button"
              onClick={submit}
              disabled={busy}
              className="nav-link mb-0.5 inline-flex w-full shrink-0 items-center justify-center gap-2 whitespace-nowrap rounded-full bg-ink px-6 py-3.5 text-cream transition hover:bg-forest disabled:opacity-70 sm:w-auto"
            >
              {busy ? (uploading ? p.uploading : s.working) : submitLabel}
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

      <div className="mt-5" hidden={mode !== "general_video"}>
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

function Field({
  label,
  value,
  onChange,
  placeholder,
  disabled,
  inputMode,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  disabled?: boolean;
  inputMode?: "text" | "decimal";
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-[11.5px] text-ink-soft/70">{label}</span>
      <input
        type="text"
        inputMode={inputMode}
        value={value}
        disabled={disabled}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-xl border border-ink/15 bg-white/60 px-3 py-2 text-[13px] text-ink outline-none transition placeholder:text-ink-soft/40 focus:border-ink/45 disabled:opacity-60"
      />
    </label>
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
