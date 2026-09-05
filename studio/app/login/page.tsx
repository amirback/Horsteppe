"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setInfo(null);
    setLoading(true);
    const supabase = createClient();
    try {
      if (mode === "signup") {
        const { data, error } = await supabase.auth.signUp({ email, password });
        if (error) {
          setError(translateAuthError(error.message));
          return;
        }
        if (!data.session) {
          setInfo("Проверьте почту и подтвердите адрес, затем войдите.");
          setMode("signin");
          return;
        }
      } else {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) {
          setError(translateAuthError(error.message));
          return;
        }
      }
      router.push("/");
      router.refresh();
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-sm pt-8">
      <div className="mb-8 text-center">
        <h1 className="text-3xl font-semibold tracking-tight">
          {mode === "signin" ? "С возвращением" : "Создать аккаунт"}
        </h1>
        <p className="mt-2 text-sm text-neutral-400">
          {mode === "signin" ? "Войдите, чтобы продолжить" : "Это займёт меньше минуты"}
        </p>
      </div>

      <form onSubmit={handleSubmit} className="card space-y-4 p-8">
        <div>
          <label htmlFor="email" className="label mb-2 block">
            Email
          </label>
          <input
            id="email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="input-field"
          />
        </div>
        <div>
          <label htmlFor="password" className="label mb-2 block">
            Пароль
          </label>
          <input
            id="password"
            type="password"
            required
            minLength={6}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Минимум 6 символов"
            className="input-field"
          />
        </div>

        {error && (
          <p className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            {error}
          </p>
        )}
        {info && (
          <p className="rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-neutral-300">
            {info}
          </p>
        )}

        <button type="submit" disabled={loading} className="btn-primary w-full">
          {loading ? "…" : mode === "signin" ? "Войти" : "Зарегистрироваться"}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-neutral-400">
        {mode === "signin" ? (
          <>
            Нет аккаунта?{" "}
            <button onClick={() => setMode("signup")} className="font-medium text-white hover:underline">
              Зарегистрироваться
            </button>
          </>
        ) : (
          <>
            Уже есть аккаунт?{" "}
            <button onClick={() => setMode("signin")} className="font-medium text-white hover:underline">
              Войти
            </button>
          </>
        )}
      </p>
    </div>
  );
}

function translateAuthError(message: string): string {
  if (message.includes("Invalid login credentials")) return "Неверный email или пароль";
  if (message.includes("already registered")) return "Этот email уже зарегистрирован";
  if (message.includes("rate limit")) return "Слишком много попыток, подождите минуту";
  return message;
}
