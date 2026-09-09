import { notFound } from "next/navigation";
import { Home } from "../components/Home";
import { getSessionEmail } from "../lib/session";
import { isLang } from "../lib/i18n";

export default async function Page({ params }: { params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  if (!isLang(lang)) notFound();
  const email = await getSessionEmail();
  return <Home lang={lang} email={email} />;
}
