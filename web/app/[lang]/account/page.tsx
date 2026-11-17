import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Account } from "../../components/Account";
import { account } from "../../lib/account-content";
import { pageMetadata } from "../../lib/seo";
import { isLang } from "../../lib/i18n";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ lang: string }>;
}): Promise<Metadata> {
  const { lang } = await params;
  if (!isLang(lang)) return {};
  return pageMetadata(lang, "/account", { title: account[lang].title, index: false });
}

export default async function Page({ params }: { params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  if (!isLang(lang)) notFound();
  return <Account lang={lang} />;
}
