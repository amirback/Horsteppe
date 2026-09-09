import { notFound } from "next/navigation";
import { ProjectsList } from "../../components/ProjectsList";
import { getSessionEmail } from "../../lib/session";
import { isLang } from "../../lib/i18n";

export default async function Page({ params }: { params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  if (!isLang(lang)) notFound();
  const email = await getSessionEmail();
  return <ProjectsList lang={lang} email={email} />;
}
