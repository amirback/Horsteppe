"use client";

import { useCallback, useEffect, useRef } from "react";

/** Чем закончился один опрос. */
export type PollOutcome =
  /** Состояние промежуточное — спросить ещё раз через обычный интервал. */
  | "continue"
  /** Состояние окончательное или спрашивать бессмысленно — остановиться. */
  | "stop"
  /** Сбой сети или сервера — спросить позже, с растущей паузой. */
  | "error";

/** Дольше этого пауза не растёт: человек ждёт ролик, а не вечность. */
const MAX_BACKOFF_MS = 60_000;

/**
 * Опрос сервера, который не течёт.
 *
 * Прежние страницы крутили опрос через setTimeout в эффекте, и у этого было
 * три изъяна.
 *
 * Утечка. Кнопка «Попробовать снова» запускала второй цикл опроса мимо
 * эффекта. Если человек уходил со страницы, пока шёл запрос, цикл после
 * ответа ставил следующий таймер — и опрашивал сервер вечно, уже без
 * страницы.
 *
 * Фоновая вкладка. Сборка идёт 5–10 минут, и всё это время спрятанная
 * вкладка дёргала сервер каждые три секунды: две сотни запросов, каждый —
 * проверка сессии и три запроса к базе. Теперь опрос засыпает, пока вкладку
 * не видно, и просыпается сразу, как её открыли.
 *
 * Сбои. На обрыве связи опрос бил в сервер с той же частотой. Теперь пауза
 * растёт вдвое на каждой неудаче, до минуты.
 *
 * Возвращает функцию перезапуска — для случаев, когда опрос остановился на
 * окончательном состоянии, а потом оно изменилось по воле человека.
 */
export function usePolling(tick: () => Promise<PollOutcome>, intervalMs: number): () => void {
  const tickRef = useRef(tick);
  useEffect(() => {
    tickRef.current = tick;
  }, [tick]);

  const state = useRef({
    alive: false,
    stopped: false,
    paused: false,
    running: false,
    failures: 0,
    timer: undefined as ReturnType<typeof setTimeout> | undefined,
  });

  const run = useCallback(async (): Promise<void> => {
    const s = state.current;
    if (!s.alive || s.running || s.stopped) return;
    if (s.timer) {
      clearTimeout(s.timer);
      s.timer = undefined;
    }
    if (document.hidden) {
      s.paused = true;
      return;
    }

    s.running = true;
    let outcome: PollOutcome;
    try {
      outcome = await tickRef.current();
    } catch {
      outcome = "error";
    }
    s.running = false;

    // Страницу закрыли, пока шёл запрос: ответ никому не нужен.
    if (!s.alive) return;
    if (outcome === "stop") {
      s.stopped = true;
      return;
    }
    s.failures = outcome === "error" ? s.failures + 1 : 0;
    const delay = Math.min(intervalMs * 2 ** s.failures, MAX_BACKOFF_MS);
    s.timer = setTimeout(() => void run(), delay);
  }, [intervalMs]);

  useEffect(() => {
    const s = state.current;
    s.alive = true;
    s.stopped = false;
    s.paused = false;
    void run();

    const onVisibility = () => {
      if (!document.hidden && s.paused) {
        s.paused = false;
        void run();
      }
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      s.alive = false;
      if (s.timer) clearTimeout(s.timer);
      s.timer = undefined;
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [run]);

  return useCallback(() => {
    const s = state.current;
    s.stopped = false;
    s.paused = false;
    s.failures = 0;
    void run();
  }, [run]);
}
