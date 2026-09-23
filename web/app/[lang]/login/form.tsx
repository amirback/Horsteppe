"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import type { Lang } from "../../lib/i18n";
import { studio } from "../../lib/studio-content";
import { Logo } from "../../components/ui";
import { Ambience } from "../../components/Ambience";

/**
 * Куда вернуть человека после входа.
 *
 * Адрес приходит из строки запроса, то есть его может подставить кто угодно.
 * Принимается только путь внутри сайта на том же языке; «//чужой.сайт» и
 * «/en\\@чужой.сайт» браузер понял бы как переход на другой домен.
 */
function safeNext(next: string | null, lang: Lang): string {
  const home = `/${lang}`;
  if (!next) return home;
  if (next !== home && !next.startsWith(`${home}/`) && !next.startsWith(`${home}?`) && !next.startsWith(`${home}#`)) {
    return home;
  }
  if (next.includes("//") || next.includes("\\")) return home;
  return next;
}

/** Вход и регистрация. Аккаунт нужен, чтобы лимиты защищали бюджет генерации. */
export function LoginForm({ lang }: { lang: Lang }) {
  const s = studio[lang].auth;
  const errors = studio[lang].errors;
  const router = useRouter();
  const search = useSearchParams();
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (busy) return;
    setError(null);
    setBusy(true);
    // Кнопка отпускается только при неудаче. После успешного входа идёт
    // переход, и отпущенная кнопка давала нажать её второй раз.
    let leaving = false;
    try {
      const supabase = createClient();
      if (mode === "signup") {
        // Аккаунт создаёт сервер и сразу подтверждает адрес: встроенная почта
        // Supabase ограничена несколькими письмами в час на весь проект, и на
        // ней регистрация нового человека попросту не работала.
        const res = await fetch("/api/auth/signup", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        });
        if (!res.ok) {
          const body = (await res.json().catch(() => ({}))) as { error?: string };
          setError(errors[body.error ?? "unknown"] ?? errors.unknown);
          return;
        }
      }
      const { error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) {
        setError(mode === "signup" ? errors.signup_failed : errors.bad_credentials);
        return;
      }
      leaving = true;
      router.push(safeNext(search.get("next"), lang));
      router.refresh();
    } catch {
      setError(errors.network);
    } finally {
      if (!leaving) setBusy(false);
    }
  }

  return (
    <div className="min-h-screen">
      <Ambience />
      <header className="border-b border-ink/10">
        <div className="container-x flex h-24 items-center md:h-28">
          <Link href={`/${lang}`} aria-label="Horsteppe">
            <Logo />
          </Link>
        </div>
      </header>

      <main className="container-x flex justify-center py-16 md:py-24">
        <div className="w-full max-w-[420px]">
          <h1 className="font-display text-[28px] font-bold tracking-[-0.02em] text-ink">{s.title}</h1>
          <p className="mt-2.5 text-[14.5px] leading-relaxed text-ink-soft/80">{s.lead}</p>

          <form onSubmit={handleSubmit} className="mt-8 space-y-4">
            <div>
              <label htmlFor="email" className="nav-link text-ink-soft/60">
                {s.email}
              </label>
              <input
                id="email"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-2 w-full rounded-2xl border-[1.5px] border-ink/20 bg-white/60 px-4 py-3 text-[15px] text-ink outline-none transition focus:border-ink"
              />
            </div>
            <div>
              <label htmlFor="password" className="nav-link text-ink-soft/60">
                {s.password}
              </label>
              <input
                id="password"
                type="password"
                required
                // Минимум действует только на регистрации: у прежних
                // аккаунтов пароли по шесть символов, и форма не должна
                // запрещать им входить.
                minLength={mode === "signup" ? 8 : undefined}
                maxLength={72}
                autoComplete={mode === "signin" ? "current-password" : "new-password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-2 w-full rounded-2xl border-[1.5px] border-ink/20 bg-white/60 px-4 py-3 text-[15px] text-ink outline-none transition focus:border-ink"
              />
            </div>

            {error ? (
              <p role="alert" className="rounded-2xl border border-ember/40 bg-white/60 px-4 py-3 text-[13.5px] text-ember">
                {error}
              </p>
            ) : null}

            <button
              type="submit"
              disabled={busy}
              className="nav-link w-full rounded-full bg-ink px-6 py-3.5 text-cream transition hover:bg-forest disabled:opacity-70"
            >
              {busy ? s.working : mode === "signin" ? s.signIn : s.signUp}
            </button>
          </form>

          <button
            type="button"
            onClick={() => {
              setMode(mode === "signin" ? "signup" : "signin");
              setError(null);
            }}
            className="mt-6 w-full text-center text-[13.5px] text-ink-soft/70 underline decoration-ink/20 underline-offset-4 transition hover:text-ink"
          >
            {mode === "signin" ? s.toSignUp : s.toSignIn}
          </button>
        </div>
      </main>
    </div>
  );
}
