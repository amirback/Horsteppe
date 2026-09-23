import type { Metadata } from "next";
import { Suspense } from "react";
import { notFound } from "next/navigation";
import { pageMetadata } from "../../lib/seo";
import { studio } from "../../lib/studio-content";
import { isLang } from "../../lib/i18n";
import { LoginForm } from "./form";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ lang: string }>;
}): Promise<Metadata> {
  const { lang } = await params;
  if (!isLang(lang)) return {};
  return pageMetadata(lang, "/login", { title: studio[lang].auth.signIn, index: false });
}

export default async function LoginPage({
  params,
}: {
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;
  if (!isLang(lang)) notFound();

  // useSearchParams внутри формы требует границы Suspense,
  // иначе страницу нельзя собрать статически.
  return (
    <Suspense fallback={<div className="min-h-screen bg-paper" />}>
      <LoginForm lang={lang} />
    </Suspense>
  );
}
