import { notFound } from "next/navigation";
import { PricingPage } from "../../components/PricingPage";
import { getSessionEmail } from "../../lib/session";
import { isLang } from "../../lib/i18n";

export default async function Page({ params }: { params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  if (!isLang(lang)) notFound();
  const email = await getSessionEmail();
  return <PricingPage lang={lang} email={email} />;
}
