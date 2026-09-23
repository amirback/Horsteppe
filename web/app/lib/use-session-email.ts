"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";

/**
 * Почта вошедшего человека — для шапки сайта.
 *
 * Раньше её узнавал сервер: каждая страница, включая главную и правовые
 * тексты, читала cookie сессии, и из-за этого отрисовывалась заново на
 * каждый визит вместо того, чтобы отдаваться готовой с CDN за миллисекунды.
 * Холодный старт серверной функции — это секунда-две белого экрана на
 * первом визите, то есть на самом важном.
 *
 * Теперь страницы статичны, а шапка узнаёт о входе сама, в браузере.
 * `getSession()` читает cookie локально, без сетевого запроса.
 *
 * Это значение только для показа — аватар и пункт меню. Права проверяет
 * сервер в каждом запросе к API, и подделка cookie ничего не откроет.
 *
 * undefined — ещё не знаем; null — не вошёл; строка — почта.
 */
export function useSessionEmail(initial?: string | null): string | null | undefined {
  const [email, setEmail] = useState<string | null | undefined>(initial);

  useEffect(() => {
    let alive = true;
    let unsubscribe: (() => void) | undefined;
    try {
      const supabase = createClient();
      supabase.auth
        .getSession()
        .then(({ data }) => {
          if (alive) setEmail(data.session?.user.email ?? null);
        })
        .catch(() => {
          if (alive) setEmail(null);
        });
      // Вход и выход на той же странице меняют шапку сразу, без перезагрузки.
      const { data } = supabase.auth.onAuthStateChange((_event, session) => {
        if (alive) setEmail(session?.user.email ?? null);
      });
      unsubscribe = () => data.subscription.unsubscribe();
    } catch {
      // Сайт без подключённой базы: входа нет и быть не может.
      setEmail(null);
    }
    return () => {
      alive = false;
      unsubscribe?.();
    };
  }, []);

  return email;
}
