import type { NextConfig } from "next";

/**
 * Заголовки безопасности для каждого ответа.
 *
 * До этого прод отдавал только HSTS, который ставит сама площадка. Не было
 * запрета на встраивание в чужой фрейм — страницу входа можно было подложить
 * под прозрачную кнопку на стороннем сайте и увести пароль (кликджекинг).
 *
 * Политика содержимого намеренно узкая: она запрещает фреймы, плагины и
 * подмену базового адреса, но не трогает скрипты. Строгая политика для
 * скриптов требует одноразовых меток на каждый ответ, а их Next.js ставит
 * только при динамической отрисовке — лендинг стал бы медленнее ради защиты
 * от атаки, которой нечем воспользоваться: пользовательский текст на сайте
 * не выводится как HTML.
 */
const SECURITY_HEADERS = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  {
    key: "Permissions-Policy",
    // Выбор фото с камеры телефона идёт через <input type=file> и этим не
    // затрагивается: запрещён только прямой доступ из скриптов.
    value: "camera=(), microphone=(), geolocation=(), browsing-topics=()",
  },
  {
    key: "Content-Security-Policy",
    value: "frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'",
  },
];

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Заголовок X-Powered-By сообщает всем версию стека и ничего не даёт взамен.
  poweredByHeader: false,
  async headers() {
    return [{ source: "/:path*", headers: SECURITY_HEADERS }];
  },
};

export default nextConfig;
