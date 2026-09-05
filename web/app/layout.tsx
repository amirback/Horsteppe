import type { Metadata, Viewport } from "next";
import { Montserrat, Inter } from "next/font/google";
import "./globals.css";

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

const SITE_URL = "https://horsteppe.vercel.app";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "Horsteppe — Orchestrating the Steppe",
    template: "%s · Horsteppe",
  },
  description:
    "Horsteppe is the pipeline that harnesses AI to create your video masterpiece: it writes the script, plans the scenes, generates the visuals, records the voice, edits and delivers a finished MP4.",
  keywords: ["AI video", "video generation", "AI director", "text to video", "AI editing", "Horsteppe"],
  authors: [{ name: "Horsteppe" }],
  openGraph: {
    type: "website",
    url: SITE_URL,
    siteName: "Horsteppe",
    title: "Horsteppe — Orchestrating the Steppe",
    description: "The pipeline that harnesses AI to create your video masterpiece.",
  },
  twitter: {
    card: "summary_large_image",
    title: "Horsteppe — Orchestrating the Steppe",
    description: "The pipeline that harnesses AI to create your video masterpiece.",
  },
  robots: { index: true, follow: true },
};

export const viewport: Viewport = {
  themeColor: "#2c5223",
  colorScheme: "light",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${montserrat.variable} ${inter.variable}`}>
      <body className="min-h-screen bg-paper text-ink antialiased">{children}</body>
    </html>
  );
}
