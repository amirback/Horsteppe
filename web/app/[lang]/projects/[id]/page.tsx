import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { pageMetadata } from "../../../lib/seo";
import { studio } from "../../../lib/studio-content";
import { isLang } from "../../../lib/i18n";
import { ProjectStatus } from "./status";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ lang: string; id: string }>;
}): Promise<Metadata> {
  const { lang, id } = await params;
  if (!isLang(lang)) return {};
  return pageMetadata(lang, `/projects/${id}`, { title: studio[lang].library.title, index: false });
}

export default async function ProjectPage({
  params,
}: {
  params: Promise<{ lang: string; id: string }>;
}) {
  const { lang, id } = await params;
  if (!isLang(lang)) notFound();
  return <ProjectStatus lang={lang} projectId={id} />;
}
