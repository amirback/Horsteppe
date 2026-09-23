import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { PricingPage } from "../../components/PricingPage";
import { pageMetadata } from "../../lib/seo";
import { content } from "../../lib/content";
import { isLang } from "../../lib/i18n";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ lang: string }>;
}): Promise<Metadata> {
  const { lang } = await params;
  if (!isLang(lang)) return {};
  return pageMetadata(lang, "/pricing", { title: content[lang].nav.pricing });
}

export default async function Page({ params }: { params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  if (!isLang(lang)) notFound();
  return <PricingPage lang={lang} />;
}
