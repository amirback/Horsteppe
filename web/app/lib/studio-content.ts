import type { Lang } from "./i18n";

export type Option = { value: string; label: string };

export type StudioDict = {
  placeholder: string;
  submit: string;
  working: string;
  style: { label: string; options: Option[] };
  duration: { label: string; options: Option[] };
  format: { label: string; options: Option[] };
  /** Честная строка под формой — её видно ДО отправки, а не после. */
  notice: string;
  examplesLabel: string;
  examples: string[];
  brief: {
    title: string;
    lead: string;
    prompt: string;
    settings: string;
    send: string;
    copy: string;
    copied: string;
    back: string;
    steps: string[];
  };
  empty: string;
};

export const studio: Record<Lang, StudioDict> = {
  en: {
    placeholder: "Describe the video you want…",
    submit: "Create video",
    working: "Preparing…",
    style: {
      label: "Style",
      options: [
        { value: "cinematic", label: "Cinematic" },
        { value: "documentary", label: "Documentary" },
        { value: "explainer", label: "Explainer" },
        { value: "product", label: "Product ad" },
        { value: "anime", label: "Anime" },
      ],
    },
    duration: {
      label: "Length",
      options: [
        { value: "15", label: "15 sec" },
        { value: "30", label: "30 sec" },
        { value: "60", label: "60 sec" },
      ],
    },
    format: {
      label: "Format",
      options: [
        { value: "9:16", label: "9:16 · Shorts" },
        { value: "16:9", label: "16:9 · YouTube" },
        { value: "1:1", label: "1:1 · Feed" },
      ],
    },
    notice:
      "Early access: we run generations one at a time, by hand. Send your brief and we return the finished video — usually the same day.",
    examplesLabel: "Or start from one of these",
    examples: [
      "The last astronaut on Earth hears a signal from an empty city",
      "How a mountain river becomes drinking water, in 30 seconds",
      "A ceramic mug ad: morning light, slow steam, one hand",
    ],
    brief: {
      title: "Your brief is ready",
      lead: "Send it in one click. We take it into work by hand and return the finished MP4.",
      prompt: "Idea",
      settings: "Settings",
      send: "Send the brief",
      copy: "Copy",
      copied: "Copied",
      back: "Edit",
      steps: [
        "We read the brief and write the script",
        "The system plans the scenes and generates the visuals",
        "Voice, subtitles, edit — and the finished video comes back to you",
      ],
    },
    empty: "Write a couple of sentences about the video first.",
  },

  ru: {
    placeholder: "Опишите ролик, который нужен…",
    submit: "Создать видео",
    working: "Готовим…",
    style: {
      label: "Стиль",
      options: [
        { value: "cinematic", label: "Кинематографично" },
        { value: "documentary", label: "Документально" },
        { value: "explainer", label: "Объяснялка" },
        { value: "product", label: "Реклама товара" },
        { value: "anime", label: "Аниме" },
      ],
    },
    duration: {
      label: "Длина",
      options: [
        { value: "15", label: "15 сек" },
        { value: "30", label: "30 сек" },
        { value: "60", label: "60 сек" },
      ],
    },
    format: {
      label: "Формат",
      options: [
        { value: "9:16", label: "9:16 · Shorts" },
        { value: "16:9", label: "16:9 · YouTube" },
        { value: "1:1", label: "1:1 · Лента" },
      ],
    },
    notice:
      "Ранний доступ: мы запускаем генерации по одной, вручную. Отправьте бриф — вернём готовый ролик, обычно в тот же день.",
    examplesLabel: "Или начните с примера",
    examples: [
      "Последний астронавт на Земле слышит сигнал из пустого города",
      "Как горная река становится питьевой водой, за 30 секунд",
      "Реклама керамической кружки: утренний свет, медленный пар, одна рука",
    ],
    brief: {
      title: "Бриф готов",
      lead: "Отправьте в один клик. Мы берём его в работу руками и возвращаем готовый MP4.",
      prompt: "Идея",
      settings: "Настройки",
      send: "Отправить бриф",
      copy: "Скопировать",
      copied: "Скопировано",
      back: "Изменить",
      steps: [
        "Читаем бриф и пишем сценарий",
        "Система планирует сцены и создаёт визуал",
        "Голос, субтитры, монтаж — и готовый ролик возвращается вам",
      ],
    },
    empty: "Сначала напишите пару предложений о ролике.",
  },

  kk: {
    placeholder: "Қандай ролик керегін сипаттаңыз…",
    submit: "Бейне жасау",
    working: "Дайындап жатырмыз…",
    style: {
      label: "Стиль",
      options: [
        { value: "cinematic", label: "Кинематографиялық" },
        { value: "documentary", label: "Деректі" },
        { value: "explainer", label: "Түсіндірме" },
        { value: "product", label: "Тауар жарнамасы" },
        { value: "anime", label: "Аниме" },
      ],
    },
    duration: {
      label: "Ұзақтығы",
      options: [
        { value: "15", label: "15 сек" },
        { value: "30", label: "30 сек" },
        { value: "60", label: "60 сек" },
      ],
    },
    format: {
      label: "Пішім",
      options: [
        { value: "9:16", label: "9:16 · Shorts" },
        { value: "16:9", label: "16:9 · YouTube" },
        { value: "1:1", label: "1:1 · Лента" },
      ],
    },
    notice:
      "Ерте қолжетімділік: генерацияны бір-бірлеп, қолмен жүргіземіз. Брифті жіберіңіз — дайын роликті қайтарамыз, әдетте сол күні.",
    examplesLabel: "Немесе мысалдан бастаңыз",
    examples: [
      "Жердегі соңғы ғарышкер бос қаладан сигнал естиді",
      "Тау өзені қалай ауыз суға айналады, 30 секундта",
      "Керамика кружкасының жарнамасы: таңғы жарық, баяу бу, бір қол",
    ],
    brief: {
      title: "Бриф дайын",
      lead: "Бір басумен жіберіңіз. Оны қолмен жұмысқа аламыз және дайын MP4 қайтарамыз.",
      prompt: "Идея",
      settings: "Баптаулар",
      send: "Брифті жіберу",
      copy: "Көшіру",
      copied: "Көшірілді",
      back: "Өзгерту",
      steps: [
        "Брифті оқып, сценарий жазамыз",
        "Жүйе сценаларды жоспарлап, кадр жасайды",
        "Дауыс, субтитр, монтаж — дайын ролик сізге қайтады",
      ],
    },
    empty: "Алдымен ролик туралы бірер сөйлем жазыңыз.",
  },
};
