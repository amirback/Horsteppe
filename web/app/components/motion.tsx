"use client";

import {
  motion,
  useInView,
  useMotionValue,
  useScroll,
  useSpring,
  useTransform,
  type MotionValue,
} from "motion/react";
import { useEffect, useRef, useState, type ReactNode } from "react";

/** Экспоненциальное замедление — движение начинается быстро и мягко тормозит. */
const EASE = [0.16, 1, 0.3, 1] as const;

/* ------------------------------------------------------- появление блока -- */

export function Reveal({
  children,
  delay = 0,
  y = 28,
  className = "",
}: {
  children: ReactNode;
  delay?: number;
  y?: number;
  className?: string;
}) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-12% 0px -8% 0px" }}
      transition={{ duration: 0.85, delay, ease: EASE }}
    >
      {children}
    </motion.div>
  );
}

/** Контейнер, дети которого появляются каскадом. */
export function Stagger({
  children,
  className = "",
  gap = 0.07,
  delay = 0,
}: {
  children: ReactNode;
  className?: string;
  gap?: number;
  delay?: number;
}) {
  return (
    <motion.div
      className={className}
      initial="hidden"
      whileInView="shown"
      viewport={{ once: true, margin: "-10% 0px -6% 0px" }}
      variants={{ hidden: {}, shown: { transition: { staggerChildren: gap, delayChildren: delay } } }}
    >
      {children}
    </motion.div>
  );
}

export function StaggerItem({
  children,
  className = "",
  y = 24,
}: {
  children: ReactNode;
  className?: string;
  y?: number;
}) {
  return (
    <motion.div
      className={className}
      variants={{
        hidden: { opacity: 0, y },
        shown: { opacity: 1, y: 0, transition: { duration: 0.8, ease: EASE } },
      }}
    >
      {children}
    </motion.div>
  );
}

/* ------------------------------------------------- заголовок по словам -- */

export function Words({
  text,
  className = "",
  delay = 0,
}: {
  text: string;
  className?: string;
  delay?: number;
}) {
  const words = text.split(" ");
  return (
    <motion.span
      className={className}
      initial="hidden"
      animate="shown"
      variants={{ hidden: {}, shown: { transition: { staggerChildren: 0.075, delayChildren: delay } } }}
      aria-label={text}
    >
      {words.map((word, i) => (
        <span key={`${word}-${i}`} className="inline-block overflow-hidden align-bottom">
          <motion.span
            className="inline-block"
            aria-hidden="true"
            variants={{
              hidden: { y: "110%", opacity: 0 },
              shown: { y: "0%", opacity: 1, transition: { duration: 0.95, ease: EASE } },
            }}
          >
            {word}
            {i < words.length - 1 ? " " : ""}
          </motion.span>
        </span>
      ))}
    </motion.span>
  );
}

/* --------------------------------------------------------------- прочее -- */

/** Элемент слегка тянется к курсору — приём с phantom.com. */
export function Magnetic({
  children,
  strength = 0.28,
  className = "",
}: {
  children: ReactNode;
  strength?: number;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const x = useSpring(useMotionValue(0), { stiffness: 180, damping: 18, mass: 0.4 });
  const y = useSpring(useMotionValue(0), { stiffness: 180, damping: 18, mass: 0.4 });
  const [fine, setFine] = useState(false);

  useEffect(() => {
    // На тач-экранах магнит бессмыслен и мешает попадать по кнопке.
    setFine(window.matchMedia("(hover: hover) and (pointer: fine)").matches);
  }, []);

  return (
    <motion.div
      ref={ref}
      className={`inline-block ${className}`}
      style={fine ? { x, y } : undefined}
      onPointerMove={(event) => {
        if (!fine || !ref.current) return;
        const r = ref.current.getBoundingClientRect();
        x.set((event.clientX - (r.left + r.width / 2)) * strength);
        y.set((event.clientY - (r.top + r.height / 2)) * strength);
      }}
      onPointerLeave={() => {
        x.set(0);
        y.set(0);
      }}
    >
      {children}
    </motion.div>
  );
}

/** Полоса прогресса чтения вверху страницы. */
export function ScrollProgress() {
  const { scrollYProgress } = useScroll();
  const scaleX = useSpring(scrollYProgress, { stiffness: 140, damping: 26, restDelta: 0.001 });
  return (
    <motion.div
      aria-hidden="true"
      style={{ scaleX }}
      className="fixed inset-x-0 top-0 z-[60] h-[3px] origin-left bg-gradient-to-r from-sage via-olive to-lime"
    />
  );
}

/** Бесконечная бегущая строка. Дублирует содержимое, чтобы стык был незаметен. */
export function Marquee({
  children,
  speed = 38,
  className = "",
}: {
  children: ReactNode;
  speed?: number;
  className?: string;
}) {
  return (
    <div className={`group relative flex overflow-hidden ${className}`}>
      {[0, 1].map((copy) => (
        <motion.div
          key={copy}
          className="flex shrink-0 items-center gap-4 pr-4"
          aria-hidden={copy === 1}
          animate={{ x: ["0%", "-100%"] }}
          transition={{ duration: speed, ease: "linear", repeat: Infinity }}
        >
          {children}
        </motion.div>
      ))}
    </div>
  );
}

/** Значение прокрутки элемента, пересчитанное в сдвиг — для параллакса. */
export function useParallax(distance = 90): {
  ref: React.RefObject<HTMLDivElement | null>;
  y: MotionValue<number>;
} {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end start"] });
  const y = useTransform(scrollYProgress, [0, 1], [0, distance]);
  return { ref, y };
}

/** Полоса, растущая до нужной доли при появлении в кадре. */
export function GrowBar({ percent, className = "" }: { percent: number; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: "-15% 0px" });
  return (
    <div ref={ref} className="h-2 overflow-hidden rounded-full bg-ink/10">
      <motion.div
        className={`h-full rounded-full ${className}`}
        initial={{ width: 0 }}
        animate={inView ? { width: `${percent}%` } : { width: 0 }}
        transition={{ duration: 1.1, ease: EASE, delay: 0.1 }}
      />
    </div>
  );
}

export { motion, EASE };
