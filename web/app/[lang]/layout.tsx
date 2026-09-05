import type { Metadata, Viewport } from "next";
import { Montserrat, Inter } from "next/font/google";
import { notFound } from "next/navigation";
import "../globals.css";
import { LOCALES, LOCALE_META, SITE_URL, isLang, type Lang } from "../lib/i18n";

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

const SEO: Record<Lang, { title: string; description: string }> = {
  en: {
    title: "Horsteppe — Orchestrating the Steppe",
    description:
      "The pipeline that harnesses AI to create your video masterpiece: it writes the script, plans the scenes, generates the visuals, records the voice, edits and delivers a finished MP4.",
  },
  ru: {
    title: "Horsteppe — оркестровка степи",
    description:
      "Конвейер, который направляет ИИ на создание вашего видеошедевра: пишет сценарий, планирует сцены, создаёт визуал, озвучивает, монтирует и отдаёт готовый MP4.",
  },
  kk: {
    title: "Horsteppe — дала оркестрі",
    description:
      "Жасанды интеллектті бейне-шедевріңізді жасауға жұмылдыратын конвейер: сценарий жазады, сценаларды жоспарлайды, кадр жасайды, дауыстайды, монтаждайды және дайын MP4 береді.",
  },
};

export function generateStaticParams() {
  return LOCALES.map((lang) => ({ lang }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ lang: string }>;
}): Promise<Metadata> {
  const { lang: raw } = await params;
  if (!isLang(raw)) return {};
  const seo = SEO[raw];

  // hreflang для всех языков плюс x-default — иначе поисковик считает
  // переводы дублями и показывает не тот язык.
  const languages = Object.fromEntries(
    LOCALES.map((l) => [LOCALE_META[l].htmlLang, `${SITE_URL}/${l}`])
  );

  return {
    metadataBase: new URL(SITE_URL),
    title: { default: seo.title, template: "%s · Horsteppe" },
    description: seo.description,
    alternates: {
      canonical: `${SITE_URL}/${raw}`,
      languages: { ...languages, "x-default": `${SITE_URL}/en` },
    },
    openGraph: {
      type: "website",
      url: `${SITE_URL}/${raw}`,
      siteName: "Horsteppe",
      title: seo.title,
      description: seo.description,
      locale: LOCALE_META[raw].ogLocale,
      alternateLocale: LOCALES.filter((l) => l !== raw).map((l) => LOCALE_META[l].ogLocale),
    },
    twitter: { card: "summary_large_image", title: seo.title, description: seo.description },
    robots: { index: true, follow: true },
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
      <body className="min-h-screen bg-paper text-ink antialiased">{children}</body>
    </html>
  );
}
