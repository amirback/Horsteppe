import { Suspense } from "react";
import { notFound } from "next/navigation";
import { isLang } from "../../lib/i18n";
import { LoginForm } from "./form";

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
