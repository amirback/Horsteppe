import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Admin } from "../../components/Admin";
import { isLang } from "../../lib/i18n";

export const metadata: Metadata = { title: "Касса", robots: { index: false, follow: false } };

/** Доступ проверяет API (/api/admin): страница без прав покажет «нет доступа». */
export default async function Page({ params }: { params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  if (!isLang(lang)) notFound();
  return <Admin lang={lang} />;
}
