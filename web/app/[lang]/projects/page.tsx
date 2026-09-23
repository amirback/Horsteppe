import { notFound } from "next/navigation";
import { ProjectsList } from "../../components/ProjectsList";
import { isLang } from "../../lib/i18n";

export default async function Page({ params }: { params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  if (!isLang(lang)) notFound();
  return <ProjectsList lang={lang} />;
}
