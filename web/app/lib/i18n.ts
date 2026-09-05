export const LOCALES = ["en", "ru", "kk"] as const;
export type Lang = (typeof LOCALES)[number];

export const DEFAULT_LOCALE: Lang = "en";

export const LOCALE_META: Record<Lang, { label: string; native: string; htmlLang: string; ogLocale: string }> = {
  en: { label: "EN", native: "English", htmlLang: "en", ogLocale: "en_US" },
  ru: { label: "RU", native: "Русский", htmlLang: "ru", ogLocale: "ru_RU" },
  kk: { label: "KK", native: "Қазақша", htmlLang: "kk", ogLocale: "kk_KZ" },
};

export const SITE_URL = "https://horsteppe.vercel.app";

export function isLang(value: string | undefined): value is Lang {
  return !!value && (LOCALES as readonly string[]).includes(value);
}

/** Выбирает язык по заголовку Accept-Language, не полагаясь на порядок. */
export function pickLocale(acceptLanguage: string | null): Lang {
  if (!acceptLanguage) return DEFAULT_LOCALE;
  const ranked = acceptLanguage
    .split(",")
    .map((part) => {
      const [tag, ...params] = part.trim().split(";");
      const q = params.find((p) => p.trim().startsWith("q="));
      return { tag: tag.trim().toLowerCase(), q: q ? Number(q.split("=")[1]) || 0 : 1 };
    })
    .sort((a, b) => b.q - a.q);

  for (const { tag } of ranked) {
    const base = tag.split("-")[0];
    if (isLang(base)) return base;
    // Казахстанские браузеры часто шлют kk-KZ, но нередко и просто ru-KZ
    if (base === "kz") return "kk";
  }
  return DEFAULT_LOCALE;
}

export function pathFor(lang: Lang, hash = ""): string {
  return `/${lang}${hash}`;
}
