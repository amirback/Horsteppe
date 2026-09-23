"use client";

import type { ReactNode } from "react";
import { MotionConfig } from "motion/react";

/**
 * Настройка «уменьшить движение» для анимаций на JavaScript.
 *
 * CSS-анимации сайта её уже уважали (globals.css), а анимации библиотеки
 * motion — нет: бегущая строка крутилась бесконечно, параллакс и каскады
 * работали, даже если человек выключил движение в системе. Для людей с
 * вестибулярными нарушениями это не вопрос вкуса — от такого укачивает.
 *
 * `reducedMotion="user"` отключает перемещения и масштаб, оставляя
 * прозрачность: элементы появляются, но не летят.
 */
export function MotionProvider({ children }: { children: ReactNode }) {
  return <MotionConfig reducedMotion="user">{children}</MotionConfig>;
}
