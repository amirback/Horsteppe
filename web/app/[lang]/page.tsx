import { notFound } from "next/navigation";
import { Home } from "../components/Home";
import { isLang } from "../lib/i18n";

export default async function Page({ params }: { params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  if (!isLang(lang)) notFound();
  return <Home lang={lang} />;
}
