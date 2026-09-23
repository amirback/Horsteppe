import { notFound } from "next/navigation";
import { LegalPage } from "../../components/LegalPage";
import { isLang } from "../../lib/i18n";

export default async function Page({ params }: { params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  if (!isLang(lang)) notFound();
  return <LegalPage lang={lang} doc="privacy" />;
}
