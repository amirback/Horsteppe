import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin", "cyrillic"],
  variable: "--font-inter",
  display: "swap",
});

const SITE_URL = "https://horsteppe.vercel.app";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "Horsteppe — от идеи до готового ролика",
    template: "%s · Horsteppe",
  },
  description:
    "Horsteppe — AI-режиссёр и монтажёр. Опишите видео одной фразой: система напишет сценарий, спланирует сцены, создаст визуал, озвучит, смонтирует и отдаст готовый MP4.",
  keywords: [
    "AI видео",
    "генерация видео",
    "AI режиссёр",
    "text to video",
    "AI монтаж",
    "Horsteppe",
  ],
  authors: [{ name: "Horsteppe" }],
  openGraph: {
    type: "website",
    url: SITE_URL,
    siteName: "Horsteppe",
    title: "Horsteppe — от идеи до готового ролика",
    description:
      "AI-режиссёр и монтажёр: одна идея — готовый смонтированный ролик с озвучкой и субтитрами.",
    locale: "ru_RU",
  },
  twitter: {
    card: "summary_large_image",
    title: "Horsteppe — от идеи до готового ролика",
    description:
      "AI-режиссёр и монтажёр: одна идея — готовый смонтированный ролик с озвучкой и субтитрами.",
  },
  robots: { index: true, follow: true },
};

export const viewport: Viewport = {
  themeColor: "#08070a",
  colorScheme: "dark",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ru" className={inter.variable}>
      <body className="min-h-screen bg-ink text-cream antialiased">
        {children}
      </body>
    </html>
  );
}
