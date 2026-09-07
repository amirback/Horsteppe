import { notFound } from "next/navigation";
import { isLang } from "../../../lib/i18n";
import { ProjectStatus } from "./status";

export default async function ProjectPage({
  params,
}: {
  params: Promise<{ lang: string; id: string }>;
}) {
  const { lang, id } = await params;
  if (!isLang(lang)) notFound();
  return <ProjectStatus lang={lang} projectId={id} />;
}
