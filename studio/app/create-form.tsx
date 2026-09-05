"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

const STYLES = [
  { value: "cinematic", label: "Кинематографичный" },
  { value: "anime", label: "Аниме" },
  { value: "documentary", label: "Документальный" },
  { value: "cyberpunk", label: "Киберпанк" },
  { value: "watercolor", label: "Акварель" },
];

export function CreateForm() {
  const router = useRouter();
  const [topic, setTopic] = useState("");
  const [style, setStyle] = useState("cinematic");
  const [duration, setDuration] = useState(30);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await fetch("/api/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic, style, duration_sec: duration }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.error ?? "Что-то пошло не так");
        return;
      }
      router.push(`/projects/${data.id}`);
    } catch {
      setError("Сеть недоступна, попробуйте ещё раз");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="card mx-auto max-w-2xl space-y-6 p-5 sm:p-8">
      <div className="text-center">
        <h2 className="text-xl font-semibold tracking-tight sm:text-2xl">Создать видео</h2>
        <p className="mt-1 text-sm text-neutral-400">Опишите тему — остальное сделает ИИ</p>
      </div>
      <div>
        <label htmlFor="topic" className="label mb-2 block">
          Тема видео
        </label>
        <textarea
          id="topic"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          required
          minLength={3}
          maxLength={500}
          rows={3}
          placeholder="Например: 5 фактов о космосе, которые звучат как фантастика"
          className="input-field resize-none"
        />
      </div>

      <div className="grid gap-6 sm:grid-cols-2">
        <div>
          <label htmlFor="style" className="label mb-2 block">
            Стиль
          </label>
          <select
            id="style"
            value={style}
            onChange={(e) => setStyle(e.target.value)}
            className="input-field appearance-none"
          >
            {STYLES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <div className="mb-2 flex items-baseline justify-between">
            <label htmlFor="duration" className="label">
              Длительность
            </label>
            <span className="text-sm font-medium text-neutral-300">{duration} сек</span>
          </div>
          <input
            id="duration"
            type="range"
            min={15}
            max={60}
            step={5}
            value={duration}
            onChange={(e) => setDuration(Number(e.target.value))}
            className="mt-3.5 w-full accent-white"
          />
        </div>
      </div>

      {error && (
        <p className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </p>
      )}

      <button type="submit" disabled={loading} className="btn-primary w-full">
        {loading ? "Создаём…" : "Сгенерировать видео"}
      </button>
    </form>
  );
}
