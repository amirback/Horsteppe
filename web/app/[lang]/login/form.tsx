"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import type { Lang } from "../../lib/i18n";
import { studio } from "../../lib/studio-content";
import { Logo } from "../../components/ui";
import { Ambience } from "../../components/Ambience";

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
  const [info, setInfo] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setInfo(null);
    setBusy(true);
    try {
      const supabase = createClient();
      if (mode === "signup") {
        const { data, error } = await supabase.auth.signUp({ email, password });
        if (error) {
          setError(error.message);
          return;
        }
        if (!data.session) {
          setInfo(s.confirm);
          setMode("signin");
          return;
        }
      } else {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) {
          setError(error.message);
          return;
        }
      }
      const next = search.get("next");
      router.push(next && next.startsWith(`/${lang}`) ? next : `/${lang}`);
      router.refresh();
    } catch {
      setError(errors.network);
    } finally {
      setBusy(false);
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
                minLength={6}
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
            {info ? (
              <p className="rounded-2xl border border-ink/15 bg-white/60 px-4 py-3 text-[13.5px] text-ink-soft">
                {info}
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
