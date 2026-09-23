import type { Metadata, Viewport } from "next";
import { Montserrat, Inter } from "next/font/google";
import { notFound } from "next/navigation";
import "../globals.css";
import { LOCALES, LOCALE_META, SITE_URL, isLang } from "../lib/i18n";
import { SEO } from "../lib/seo";
import { MotionProvider } from "../components/MotionProvider";

const montserrat = Montserrat({
  subsets: ["latin", "cyrillic"],
  variable: "--font-montserrat",
  display: "swap",
});

const inter = Inter({
  subsets: ["latin", "cyrillic"],
  variable: "--font-body",
  display: "swap",
});

export function generateStaticParams() {
  return LOCALES.map((lang) => ({ lang }));
}

/**
 * Общая основа метаданных. Адрес, связи между языками и карточку для
 * соцсетей каждая страница задаёт сама (app/lib/seo.ts): иначе все они
 * наследовали канонический адрес главной и выпадали из поиска как дубли.
 */
export async function generateMetadata({
  params,
}: {
  params: Promise<{ lang: string }>;
}): Promise<Metadata> {
  const { lang: raw } = await params;
  if (!isLang(raw)) return {};
  return {
    metadataBase: new URL(SITE_URL),
    // На вкладке — только имя бренда: описание живёт в meta description,
    // а длинный заголовок в узкой вкладке всё равно обрезается.
    title: { default: "Horsteppe", template: "%s · Horsteppe" },
    description: SEO[raw].description,
  };
}

export const viewport: Viewport = {
  themeColor: "#2c5223",
  colorScheme: "light",
};

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;
  if (!isLang(lang)) notFound();

  return (
    <html lang={LOCALE_META[lang].htmlLang} className={`${montserrat.variable} ${inter.variable}`}>
      <body className="min-h-screen bg-paper text-ink antialiased">
        {/* Если скрипты не выполнились вовсе — блокировщик, старый браузер,
            оборванная загрузка, — блоки с анимацией появления остались бы
            прозрачными навсегда: они ждут JavaScript, чтобы проявиться.
            Правило действует только когда скрипты выключены. */}
        <noscript>
          <style>{`[style*="opacity:0"]{opacity:1!important;transform:none!important}`}</style>
        </noscript>
        <MotionProvider>{children}</MotionProvider>
      </body>
    </html>
  );
}
