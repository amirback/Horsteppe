import type { Lang } from "./i18n";

/**
 * Перевод строк, которые пишет сборщик.
 *
 * Сборщик сообщает о ходе работы по-русски: «Пишем сценарий…», «Кадры:
 * 3/8». Эти строки лежат в базе и раньше показывались как есть — на
 * английской и казахской версии сайта человек видел кириллицу посреди
 * своего языка.
 *
 * Переводить в сборщике неправильно: он не знает языка посетителя, а один
 * проект могут открыть с разных версий сайта. Поэтому перевод здесь, по
 * точному списку строк сборщика. Строка, которой нет в списке, на чужом
 * языке заменяется общим текстом: русская фраза посреди английской
 * страницы хуже, чем честное «идёт сборка».
 *
 * Список обязан совпадать с тем, что пишут worker/pipeline.py и
 * worker/main.py. Казахский перевод машинный и ждёт вычитки носителем.
 */

type Localized = { en: string; kk: string };
type Rule = { re: RegExp; text: (m: RegExpMatchArray) => Localized };

const PROGRESS: Rule[] = [
  { re: /^В очереди…$/, text: () => ({ en: "Queued…", kk: "Кезекте…" }) },
  { re: /^Повторная попытка…$/, text: () => ({ en: "Retrying…", kk: "Қайта әрекет…" }) },
  { re: /^Готовим фотографии…$/, text: () => ({ en: "Preparing your photos…", kk: "Фотоларды дайындап жатырмыз…" }) },
  { re: /^Пишем сценарий…$/, text: () => ({ en: "Writing the script…", kk: "Сценарий жазып жатырмыз…" }) },
  {
    re: /^Озвучка: сцена (\d+)\/(\d+)$/,
    text: (m) => ({ en: `Voice-over: scene ${m[1]}/${m[2]}`, kk: `Дыбыстау: сахна ${m[1]}/${m[2]}` }),
  },
  { re: /^Раскадровка…$/, text: () => ({ en: "Planning the shots…", kk: "Кадрларды жоспарлап жатырмыз…" }) },
  { re: /^Кадры: (\d+)\/(\d+)$/, text: (m) => ({ en: `Images: ${m[1]}/${m[2]}`, kk: `Кадрлар: ${m[1]}/${m[2]}` }) },
  {
    re: /^Видео: кадр (\d+)\/(\d+) \(может занять несколько минут\)$/,
    text: (m) => ({
      en: `Video: shot ${m[1]}/${m[2]} (this can take a few minutes)`,
      kk: `Бейне: кадр ${m[1]}/${m[2]} (бірнеше минут кетуі мүмкін)`,
    }),
  },
  {
    re: /^Оживляем фотографию: (\d+)\/(\d+)$/,
    text: (m) => ({ en: `Animating your photo: ${m[1]}/${m[2]}`, kk: `Фотоны жандандырып жатырмыз: ${m[1]}/${m[2]}` }),
  },
  { re: /^Монтаж…$/, text: () => ({ en: "Editing…", kk: "Монтаж…" }) },
  { re: /^Проверка результата…$/, text: () => ({ en: "Checking the result…", kk: "Нәтижені тексеріп жатырмыз…" }) },
  {
    re: /^Починка кадров \(круг (\d+)\)…$/,
    text: (m) => ({ en: `Fixing shots (round ${m[1]})…`, kk: `Кадрларды түзетіп жатырмыз (${m[1]}-айналым)…` }),
  },
  { re: /^Загрузка результата…$/, text: () => ({ en: "Uploading the result…", kk: "Нәтижені жүктеп жатырмыз…" }) },
  { re: /^Готово$/, text: () => ({ en: "Ready", kk: "Дайын" }) },
  { re: /^Готово с оговоркой$/, text: () => ({ en: "Ready, with a note", kk: "Дайын, ескертпемен" }) },
];

const FAILURES: Rule[] = [
  {
    re: /^Не удалось сгенерировать видео\. Попробуйте ещё раз позже\.$/,
    text: () => ({
      en: "The video could not be produced. Please try again later.",
      kk: "Бейнені жасау мүмкін болмады. Кейінірек қайталап көріңіз.",
    }),
  },
  {
    re: /^Тема отклонена модерацией( контента)?\. Переформулируйте запрос\.$/,
    text: () => ({
      en: "The topic was declined by content moderation. Please rephrase your request.",
      kk: "Тақырыпты модерация қабылдамады. Сұрауды басқаша жазыңыз.",
    }),
  },
  { re: /^Не удалось сохранить фотографии$/, text: () => ({ en: "Your photos could not be saved.", kk: "Фотоларды сақтау мүмкін болмады." }) },
  { re: /^Не удалось прикрепить фотографии$/, text: () => ({ en: "Your photos could not be attached.", kk: "Фотоларды тіркеу мүмкін болмады." }) },
  { re: /^Ошибка постановки в очередь$/, text: () => ({ en: "The job could not be queued.", kk: "Тапсырманы кезекке қою мүмкін болмады." }) },
];

const DEGRADED: Rule[] = [
  {
    re: /^Настоящее видео отключено в этом режиме — движение сделано камерой по кадру\.$/,
    text: () => ({
      en: "Real video is turned off in this mode — the motion is a camera move across the frame.",
      kk: "Бұл режимде нақты бейне өшірулі — қозғалысты камера кадр бойымен жасады.",
    }),
  },
  {
    re: /^Бюджета хватило не на все кадры — часть осталась движением камеры\.$/,
    text: () => ({
      en: "The budget did not cover every shot — some remain camera moves over a still frame.",
      kk: "Бюджет барлық кадрға жетпеді — бір бөлігі камера қозғалысы болып қалды.",
    }),
  },
  {
    re: /^Провайдер видео ответил отказом на часть кадров\.$/,
    text: () => ({
      en: "The video provider declined some of the shots.",
      kk: "Бейне провайдері кейбір кадрлардан бас тартты.",
    }),
  },
  {
    re: /^Настоящим видео закрыта меньшая часть ролика, чем планировалось\.$/,
    text: () => ({
      en: "Less of the video is real motion than planned.",
      kk: "Нақты бейне жоспарланғаннан аз бөлігін қамтыды.",
    }),
  },
];

function translate(rules: Rule[], text: string | null | undefined, lang: Lang): string | null {
  if (!text) return null;
  if (lang === "ru") return text;
  const trimmed = text.trim();
  for (const rule of rules) {
    const m = trimmed.match(rule.re);
    if (m) return rule.text(m)[lang];
  }
  return null;
}

/** Строка хода работы. null — перевода нет, покажите общий этап. */
export function progressText(text: string | null | undefined, lang: Lang): string | null {
  return translate(PROGRESS, text, lang);
}

/** Причина провала. null — перевода нет, покажите общее сообщение. */
export function failureText(text: string | null | undefined, lang: Lang): string | null {
  return translate(FAILURES, text, lang);
}

/** Почему ролик готов с оговоркой. null — перевода нет. */
export function degradedText(text: string | null | undefined, lang: Lang): string | null {
  return translate(DEGRADED, text, lang);
}
