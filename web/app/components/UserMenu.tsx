"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";
import { content } from "../lib/content";
import { studio } from "../lib/studio-content";
import type { Lang } from "../lib/i18n";
import { motion } from "./motion";

/**
 * Меню вошедшего пользователя.
 *
 * Раньше после входа в шапке продолжала висеть кнопка «Войти», и понять,
 * вошёл ты или нет, было невозможно.
 */
export function UserMenu({ lang, email }: { lang: Lang; email: string }) {
  const t = content[lang];
  const library = studio[lang].library;
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (box.current && !box.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  async function signOut() {
    setBusy(true);
    try {
      await createClient().auth.signOut();
      router.push(`/${lang}`);
      router.refresh();
    } finally {
      setBusy(false);
      setOpen(false);
    }
  }

  const initial = email.trim().charAt(0).toUpperCase() || "?";

  return (
    <div ref={box} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="menu"
        title={email}
        className="flex h-10 w-10 items-center justify-center rounded-full border-[1.5px] border-ink/25 bg-white/50 font-display text-[14px] font-bold text-ink transition hover:border-ink"
      >
        {initial}
      </button>

      {open ? (
        <motion.div
          role="menu"
          initial={{ opacity: 0, y: -6, scale: 0.97 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.18 }}
          className="absolute right-0 top-full z-50 mt-2 w-[min(16rem,calc(100vw-2rem))] overflow-hidden rounded-2xl border border-ink/12 bg-paper shadow-[0_20px_50px_-24px_rgba(22,52,26,0.5)]"
        >
          <div className="border-b border-ink/10 px-4 py-3">
            <div className="nav-link text-ink-soft/50">{t.nav.account}</div>
            <div className="mt-1 truncate text-[13.5px] text-ink">{email}</div>
          </div>
          <Link
            href={`/${lang}/projects`}
            onClick={() => setOpen(false)}
            className="block px-4 py-3 text-[14px] text-ink-soft transition hover:bg-ink/5 hover:text-ink"
          >
            {library.title}
          </Link>
          <Link
            href={`/${lang}#top`}
            onClick={() => setOpen(false)}
            className="block px-4 py-3 text-[14px] text-ink-soft transition hover:bg-ink/5 hover:text-ink"
          >
            {t.nav.cta}
          </Link>
          <button
            type="button"
            onClick={signOut}
            disabled={busy}
            className="block w-full px-4 py-3 text-left text-[14px] text-ink-soft transition hover:bg-ink/5 hover:text-ink disabled:opacity-60"
          >
            {busy ? "…" : t.nav.signOut}
          </button>
        </motion.div>
      ) : null}
    </div>
  );
}
