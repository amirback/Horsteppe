import { notFound } from "next/navigation";
import { PricingPage } from "../../components/PricingPage";
import { isLang } from "../../lib/i18n";

export default async function Page({ params }: { params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  if (!isLang(lang)) notFound();
  return <PricingPage lang={lang} />;
}
