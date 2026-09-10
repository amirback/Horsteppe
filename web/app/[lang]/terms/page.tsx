import { notFound } from "next/navigation";
import { LegalPage } from "../../components/LegalPage";
import { getSessionEmail } from "../../lib/session";
import { isLang } from "../../lib/i18n";

export default async function Page({ params }: { params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  if (!isLang(lang)) notFound();
  const email = await getSessionEmail();
  return <LegalPage lang={lang} doc="terms" email={email} />;
}
