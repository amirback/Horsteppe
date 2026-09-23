import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { ProjectsList } from "../../components/ProjectsList";
import { pageMetadata } from "../../lib/seo";
import { studio } from "../../lib/studio-content";
import { isLang } from "../../lib/i18n";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ lang: string }>;
}): Promise<Metadata> {
  const { lang } = await params;
  if (!isLang(lang)) return {};
  return pageMetadata(lang, "/projects", { title: studio[lang].library.title, index: false });
}

export default async function Page({ params }: { params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  if (!isLang(lang)) notFound();
  return <ProjectsList lang={lang} />;
}
