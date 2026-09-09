import type { Lang } from "./i18n";

export type { Lang };

export const CONTACT_EMAIL = "Horsteppe@gmail.com";

export type Dict = {
  nav: { product: string; pricing: string; signIn: string; cta: string };
  hero: { title: string; sub: string; scroll: string };
  steps: { n: string; title: string; text: string }[];
  values: { title: string; text: string }[];
  faq: { q: string; a: string }[];
  pricing: {
    kicker: string;
    title: string;
    sub: string;
    tiers: { name: string; price: string; items: string[]; highlight?: boolean }[];
    note: string;
    cta: string;
  };
  footer: { tagline: string; contact: string; rights: string; orda: string; lang: string };
};

export const content: Record<Lang, Dict> = {
  en: {
    nav: { product: "Product", pricing: "Pricing", signIn: "Sign in", cta: "Create video" },
    hero: {
      title: "Orchestrating the Steppe.",
      sub: "Describe your video. Horsteppe writes it, shoots it, voices it and edits it.",
      scroll: "How it works",
    },
    steps: [
      { n: "01", title: "Write the idea", text: "One sentence is enough." },
      { n: "02", title: "Horsteppe produces", text: "Script, scenes, visuals, voice, subtitles, edit." },
      { n: "03", title: "Take the file", text: "A finished MP4, ready to post." },
    ],
    values: [
      {
        title: "A finished video, not clips",
        text: "Other tools hand you five seconds. Horsteppe delivers the whole thing, edited.",
      },
      {
        title: "Cost stays under control",
        text: "Expensive generation only where motion earns it. The rest is camera movement over a frame.",
      },
      {
        title: "One failure doesn't kill the run",
        text: "If a provider goes down, the pipeline switches and the video still finishes.",
      },
    ],
    faq: [
      { q: "How long does it take?", a: "A few minutes. You can close the page and come back." },
      { q: "Do I need editing skills?", a: "No. You describe the video and receive a file." },
      { q: "Who owns the result?", a: "You do." },
      {
        q: "Can I use it commercially?",
        a: "Generation relies on third-party models with their own terms, so during early access we agree it case by case.",
      },
    ],
    pricing: {
      kicker: "Pricing",
      title: "No price list yet",
      sub: "We measure what a finished video actually costs before we sell one. Until then, early access is free.",
      tiers: [
        {
          name: "Early access",
          price: "Free",
          items: ["Unlimited drafts", "Vertical and horizontal", "Voice and subtitles included", "We help by hand if something breaks"],
          highlight: true,
        },
        {
          name: "Creator",
          price: "In testing",
          items: ["Monthly allowance of premium seconds", "Project history", "Faster queue"],
        },
        {
          name: "Agency",
          price: "In testing",
          items: ["Bring your own provider key", "Batch generation", "Brand kit and presets"],
        },
      ],
      note: "Why no price: the cost of one video is driven almost entirely by premium video seconds, and that number is only known after a few dozen real runs.",
      cta: "Start creating",
    },
    footer: {
      tagline: "An AI director and editor. From an idea to the final cut.",
      contact: "Contact",
      rights: "All rights reserved.",
      orda: "Startup Orda 2",
      lang: "Language",
    },
  },

  ru: {
    nav: { product: "Продукт", pricing: "Тарифы", signIn: "Войти", cta: "Создать видео" },
    hero: {
      title: "Оркестровка степи.",
      sub: "Опишите ролик. Horsteppe напишет сценарий, снимет, озвучит и смонтирует.",
      scroll: "Как это работает",
    },
    steps: [
      { n: "01", title: "Напишите идею", text: "Хватит одного предложения." },
      { n: "02", title: "Horsteppe собирает", text: "Сценарий, сцены, кадры, голос, субтитры, монтаж." },
      { n: "03", title: "Забирайте файл", text: "Готовый MP4, можно сразу публиковать." },
    ],
    values: [
      {
        title: "Готовый ролик, а не нарезка",
        text: "Другие сервисы отдают пять секунд. Horsteppe отдаёт всё целиком и смонтированным.",
      },
      {
        title: "Себестоимость под контролем",
        text: "Дорогая генерация только там, где движение работает. Остальное — движение камеры по кадру.",
      },
      {
        title: "Один сбой не уносит проект",
        text: "Если провайдер упал, конвейер переключается, и ролик всё равно доходит до конца.",
      },
    ],
    faq: [
      { q: "Сколько занимает?", a: "Несколько минут. Страницу можно закрыть и вернуться." },
      { q: "Нужно уметь монтировать?", a: "Нет. Вы описываете видео и получаете файл." },
      { q: "Кому принадлежит результат?", a: "Вам." },
      {
        q: "Можно использовать коммерчески?",
        a: "Генерация опирается на сторонние модели со своими условиями, поэтому на раннем доступе договариваемся отдельно.",
      },
    ],
    pricing: {
      kicker: "Тарифы",
      title: "Прайса пока нет",
      sub: "Сначала измеряем, во сколько реально обходится готовый ролик. До тех пор ранний доступ бесплатный.",
      tiers: [
        {
          name: "Ранний доступ",
          price: "Бесплатно",
          items: ["Без ограничений на черновики", "Вертикально и горизонтально", "Голос и субтитры включены", "Помогаем руками, если что-то сломалось"],
          highlight: true,
        },
        {
          name: "Creator",
          price: "В проверке",
          items: ["Месячный пакет премиум-секунд", "История проектов", "Быстрая очередь"],
        },
        {
          name: "Agency",
          price: "В проверке",
          items: ["Свой ключ провайдера", "Пакетная генерация", "Бренд-кит и пресеты"],
        },
      ],
      note: "Почему цены нет: себестоимость ролика почти целиком определяется премиум-секундами видео, а это число известно только после нескольких десятков реальных прогонов.",
      cta: "Начать",
    },
    footer: {
      tagline: "AI-режиссёр и монтажёр. От идеи до финального кадра.",
      contact: "Связаться",
      rights: "Все права защищены.",
      orda: "Startup Orda 2",
      lang: "Язык",
    },
  },

  kk: {
    nav: { product: "Өнім", pricing: "Тарифтер", signIn: "Кіру", cta: "Бейне жасау" },
    hero: {
      title: "Дала оркестрі.",
      sub: "Роликті сипаттаңыз. Horsteppe сценарий жазып, түсіріп, дауыстап, монтаждайды.",
      scroll: "Қалай жұмыс істейді",
    },
    steps: [
      { n: "01", title: "Идеяны жазыңыз", text: "Бір сөйлем жеткілікті." },
      { n: "02", title: "Horsteppe жинайды", text: "Сценарий, сценалар, кадрлар, дауыс, субтитр, монтаж." },
      { n: "03", title: "Файлды алыңыз", text: "Дайын MP4, бірден жариялауға болады." },
    ],
    values: [
      {
        title: "Дайын ролик, үзінді емес",
        text: "Басқа сервистер бес секунд береді. Horsteppe бәрін толық әрі монтаждалған күйде береді.",
      },
      {
        title: "Өзіндік құн бақылауда",
        text: "Қымбат генерация тек қозғалыс жұмыс істейтін жерде. Қалғаны — кадр бойынша камера қозғалысы.",
      },
      {
        title: "Бір ақау жобаны алып кетпейді",
        text: "Провайдер құласа, конвейер ауысады және ролик бәрібір аяғына жетеді.",
      },
    ],
    faq: [
      { q: "Қанша уақыт алады?", a: "Бірнеше минут. Бетті жабуға және кейін оралуға болады." },
      { q: "Монтаж білу керек пе?", a: "Жоқ. Сіз бейнені сипаттайсыз да, файл аласыз." },
      { q: "Нәтиже кімдікі?", a: "Сіздікі." },
      {
        q: "Коммерциялық қолдануға бола ма?",
        a: "Генерация өз шарттары бар сыртқы модельдерге сүйенеді, сондықтан ерте қолжетімділікте бөлек келісеміз.",
      },
    ],
    pricing: {
      kicker: "Тарифтер",
      title: "Бағасы әлі жоқ",
      sub: "Алдымен дайын ролик шын мәнінде қанша тұратынын өлшейміз. Оған дейін ерте қолжетімділік тегін.",
      tiers: [
        {
          name: "Ерте қолжетімділік",
          price: "Тегін",
          items: ["Нобайларға шек жоқ", "Тік және көлденең", "Дауыс пен субтитр кіреді", "Бірдеңе сынса — қолмен көмектесеміз"],
          highlight: true,
        },
        {
          name: "Creator",
          price: "Тексеруде",
          items: ["Айлық премиум-секунд пакеті", "Жобалар тарихы", "Жылдам кезек"],
        },
        {
          name: "Agency",
          price: "Тексеруде",
          items: ["Өз провайдер кілтіңіз", "Топтық генерация", "Бренд-кит және пресеттер"],
        },
      ],
      note: "Неге бағасы жоқ: роликтің өзіндік құны негізінен премиум-секундтармен анықталады, ал бұл сан бірнеше ондаған нақты жүрістен кейін ғана белгілі болады.",
      cta: "Бастау",
    },
    footer: {
      tagline: "AI-режиссёр және монтажшы. Идеядан соңғы кадрға дейін.",
      contact: "Байланыс",
      rights: "Барлық құқық қорғалған.",
      orda: "Startup Orda 2",
      lang: "Тіл",
    },
  },
};
