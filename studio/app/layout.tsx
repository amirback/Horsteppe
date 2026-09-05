import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { createClient } from "@/lib/supabase/server";
import { LogoutButton } from "./logout-button";

export const metadata: Metadata = {
  title: "Reel — ИИ-видео из одной темы",
  description:
    "Введите тему — получите готовый вертикальный ролик: сценарий, кадры, озвучка и монтаж. Полностью автоматически.",
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  return (
    <html lang="ru">
      <body className="min-h-screen">
        <header className="sticky top-0 z-20 border-b border-white/10 bg-[#0a0a0c]/80 backdrop-blur-xl">
          <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
            <Link
              href="/"
              className="flex shrink-0 items-center gap-2.5 text-[15px] font-semibold tracking-tight"
            >
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 to-fuchsia-500 text-[12px] font-bold text-white">
                R
              </span>
              Reel
            </Link>

            <nav className="hidden items-center gap-7 text-sm text-neutral-400 md:flex">
              <a href="/#examples" className="transition-colors hover:text-white">
                Примеры
              </a>
              <a href="/#features" className="transition-colors hover:text-white">
                Возможности
              </a>
              <a href="/#pricing" className="transition-colors hover:text-white">
                Тарифы
              </a>
              <a href="/#faq" className="transition-colors hover:text-white">
                FAQ
              </a>
            </nav>

            <div className="flex items-center gap-3 text-sm text-neutral-400 sm:gap-4">
              {user ? (
                <>
                  <Link href="/projects" className="transition-colors hover:text-white">
                    Мои видео
                  </Link>
                  <LogoutButton />
                  <Link href="/" className="btn-primary !px-4 !py-2 max-sm:hidden">
                    + Создать
                  </Link>
                </>
              ) : (
                <Link href="/login" className="btn-primary !px-5 !py-2">
                  Войти
                </Link>
              )}
            </div>
          </div>
        </header>

        <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6 sm:py-14">{children}</main>

        <footer className="mt-24 border-t border-white/10 bg-white/[0.02]">
          <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6 sm:py-16">
            <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <div className="flex items-center gap-2.5 text-[15px] font-semibold">
                  <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 to-fuchsia-500 text-[12px] font-bold text-white">
                    R
                  </span>
                  Reel
                </div>
                <p className="mt-4 max-w-xs text-sm leading-relaxed text-neutral-500">
                  Готовое вертикальное видео из одной темы. Сценарий, кадры,
                  озвучка и монтаж — полностью автоматически.
                </p>
              </div>
              <div>
                <p className="label mb-4">Продукт</p>
                <ul className="space-y-3 text-sm text-neutral-400">
                  <li><a href="/#examples" className="transition-colors hover:text-white">Примеры стилей</a></li>
                  <li><a href="/#features" className="transition-colors hover:text-white">Возможности</a></li>
                  <li><a href="/#how" className="transition-colors hover:text-white">Как это работает</a></li>
                  <li><a href="/#pricing" className="transition-colors hover:text-white">Тарифы</a></li>
                </ul>
              </div>
              <div>
                <p className="label mb-4">Аккаунт</p>
                <ul className="space-y-3 text-sm text-neutral-400">
                  <li><Link href="/login" className="transition-colors hover:text-white">Войти</Link></li>
                  <li><Link href="/login" className="transition-colors hover:text-white">Регистрация</Link></li>
                  <li><Link href="/projects" className="transition-colors hover:text-white">Мои видео</Link></li>
                </ul>
              </div>
              <div>
                <p className="label mb-4">Помощь</p>
                <ul className="space-y-3 text-sm text-neutral-400">
                  <li><a href="/#faq" className="transition-colors hover:text-white">Частые вопросы</a></li>
                  <li>
                    <a href="mailto:support@reel.app" className="transition-colors hover:text-white">
                      support@reel.app
                    </a>
                  </li>
                </ul>
              </div>
            </div>
            <div className="mt-12 flex flex-col items-center justify-between gap-4 border-t border-white/10 pt-8 text-xs text-neutral-500 sm:flex-row">
              <span>© {new Date().getFullYear()} Reel. Все права защищены.</span>
              <span>Видео генерируются ИИ и могут содержать неточности</span>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
