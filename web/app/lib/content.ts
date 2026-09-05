export type Lang = "en" | "ru";

export const CONTACT_EMAIL = "amirkhan17.01.10@gmail.com";

export type Dict = {
  nav: { home: string; product: string; team: string; pricing: string; blog: string; search: string };
  hero: { title: string; sub1: string; sub2: string; cta: string };
  problem: {
    kicker: string; title: string;
    beforeTitle: string; beforeItems: string[]; beforeFooter: string;
    afterTitle: string; afterItems: string[]; afterFooter: string;
  };
  how: { kicker: string; title: string; sub: string; steps: { n: string; title: string; text: string }[] };
  budget: {
    kicker: string; title: string; sub: string; exampleLabel: string;
    premium: string; motion: string;
    scenes: { n: number; kind: "premium" | "motion"; label: string }[];
    barNaiveLabel: string; barSmartLabel: string; footnote: string;
  };
  features: { kicker: string; title: string; items: { title: string; text: string }[] };
  roadmap: { kicker: string; title: string; sub: string; columns: { title: string; state: string; items: string[] }[] };
  demo: { kicker: string; title: string; sub: string; placeholder: string; caption: string };
  team: {
    kicker: string; title: string; sub: string;
    roles: { role: string; who: string; text: string }[];
    note: string;
  };
  pricing: {
    kicker: string; title: string; sub: string;
    tiers: { name: string; price: string; note: string; items: string[]; highlight?: boolean }[];
    footnote: string;
  };
  blog: { kicker: string; title: string; sub: string; posts: { date: string; title: string; text: string }[] };
  faq: { kicker: string; title: string; items: { q: string; a: string }[] };
  cta: { title: string; sub: string; button: string; alt: string };
  footer: { tagline: string; rights: string; contact: string; orda: string; lang: string };
  waitlist: { subject: string; body: string };
  searchUi: { placeholder: string; empty: string; close: string };
};

export const content: Record<Lang, Dict> = {
  en: {
    nav: { home: "Home", product: "Product", team: "Team", pricing: "Pricing", blog: "Blog", search: "Search" },
    hero: {
      title: "Orchestrating the Steppe.",
      sub1: "The Pipeline that Harnesses AI to Create",
      sub2: "Your Video Masterpiece.",
      cta: "Learn more",
    },
    problem: {
      kicker: "The problem",
      title: "A finished video today means seven tabs and three hours",
      beforeTitle: "How it is done now",
      beforeItems: [
        "An LLM to write the script",
        "An image generator for the frames",
        "Runway / Kling / Veo for motion",
        "ElevenLabs for the voiceover",
        "Hunting for music that is safe to use",
        "CapCut or Premiere for the edit",
        "A separate tool for subtitles",
        "And then mixing and exporting it all",
      ],
      beforeFooter:
        "Every step is its own account, its own file format and its own bill. And you still need editing skills.",
      afterTitle: "How it works here",
      afterItems: ["One input field", "One button", "A finished MP4 with voice, subtitles and music"],
      afterFooter: "We are not selling one more generation model. We are removing the workflow itself.",
    },
    how: {
      kicker: "How it works",
      title: "Six steps the system takes on its own",
      sub: "Exactly the path a small production team would follow — only automatically.",
      steps: [
        { n: "01", title: "Understands the brief", text: "Reads your sentence: format, length, tone, platform, and what result you actually need." },
        { n: "02", title: "Writes the story", text: "Builds a script with a strong hook, escalation, a climax and a clear ending — not a pile of pretty frames." },
        { n: "03", title: "Records the voice", text: "Synthesises the narration first, so the real length of the audio — not a requested number — drives every scene." },
        { n: "04", title: "Plans and shoots the scenes", text: "Breaks the story into shots and generates the frames, holding one visual style across the whole film." },
        { n: "05", title: "Adds motion", text: "Animates each frame with a controlled camera move, and spends on premium AI video only where motion truly carries the shot." },
        { n: "06", title: "Edits and delivers", text: "Assembles the timeline, adds subtitles and music, mixes the audio and exports a finished MP4." },
      ],
    },
    budget: {
      kicker: "The core idea",
      title: "Not every second is worth the same",
      sub: "Expensive AI video generation only pays off where motion genuinely carries the shot. Everything else is shot as controlled camera movement over a generated frame. Viewers barely notice the difference — the cost per video drops several times over.",
      exampleLabel: "Example allocation for a 60-second video",
      premium: "Premium AI video",
      motion: "Camera motion",
      scenes: [
        { n: 1, kind: "motion", label: "Setup" },
        { n: 2, kind: "motion", label: "Build" },
        { n: 3, kind: "premium", label: "Key moment" },
        { n: 4, kind: "motion", label: "Bridge" },
        { n: 5, kind: "premium", label: "Climax" },
      ],
      barNaiveLabel: "Generating all 60 seconds with a premium model",
      barSmartLabel: "Horsteppe: premium only where it shows",
      footnote:
        "The diagram illustrates how the planner reasons — it is not a guaranteed result for a specific video. The real allocation is computed per story.",
    },
    features: {
      kicker: "What is inside",
      title: "A production pipeline, not a wrapper around one model",
      items: [
        { title: "AI director", text: "Owns the dramaturgy: hook, escalation, climax and ending. Without it a video falls apart into random shots." },
        { title: "Scene planner", text: "Computes timing and narration density so a one-minute video does not end up voiced in fifteen seconds." },
        { title: "Smart visual budget", text: "Decides where expensive video generation is worth it and where camera motion is enough — keeping cost under control." },
        { title: "Asset reuse", text: "The same location or object is reused across scenes: less spend, more visual continuity." },
        { title: "Voice as the metronome", text: "The edit is timed to the real duration of the narration, not to a requested number of seconds." },
        { title: "Automatic editing", text: "Timeline, transitions, subtitles, audio mix and final export — with no manual work in an editor." },
        { title: "Provider independence", text: "Models are plugged in as replaceable modules. If one service goes down or gets expensive, the pipeline keeps running." },
        { title: "The video always finishes", text: "If premium generation is unavailable, the scene is rendered locally. One failing service must not kill the project." },
      ],
    },
    roadmap: {
      kicker: "Where we honestly are",
      title: "What exists today and what comes next",
      sub: "We are at the early-access stage. This is the real picture, not a checkbox list.",
      columns: [
        {
          title: "Pipeline core", state: "In closed testing",
          items: ["Idea → script → scenes", "Frame generation", "Voice and per-scene timing", "Camera motion over frames", "Assembly and MP4 export", "Cost logged for every paid call", "Resume after a failure"],
        },
        {
          title: "Next few weeks", state: "In progress",
          items: ["Subtitles burned into the video", "Transitions between scenes", "Premium AI video for key scenes", "Live generation status", "Project history"],
        },
        {
          title: "After that", state: "Planned",
          items: ["Horizontal 16:9 and automatic reframing", "One consistent character across scenes", "Editing a single scene without a full re-render", "Animated captions for Shorts and Reels", "Localising a video into other languages"],
        },
      ],
    },
    demo: {
      kicker: "Demo",
      title: "A video assembled by the system end to end",
      sub: "One sentence in. Script, frames, voice and the edit — with no human in the loop.",
      placeholder: "Demo video in production",
      caption: "The flagship example will live here. While it is being finished, we are happy to show the latest cut in person.",
    },
    team: {
      kicker: "Team",
      title: "Small on purpose",
      sub: "Three roles, clear boundaries. Nobody is doing everything at once.",
      roles: [
        { role: "Founder & product", who: "Amirkhan", text: "Product vision, priorities, customer interviews, sales and demos. And the hardest job — deciding what not to build." },
        { role: "Product engineer", who: "", text: "Front end, web integration, deployment and the database. Turns the pipeline into something a person can actually use." },
        { role: "AI coding agent", who: "", text: "Reads the repository, implements scoped tasks, runs tests and fixes integration bugs. It never decides on its own to spend money at a provider or rewrite the architecture." },
      ],
      note: "Participant of Startup Orda 2.",
    },
    pricing: {
      kicker: "Pricing",
      title: "No price list yet — and that is deliberate",
      sub: "We measure what a finished video actually costs before we sell one. Until then we take briefs by hand and quote per project. Below is the structure we are testing.",
      tiers: [
        { name: "Early access", price: "By agreement", note: "Available now", items: ["We take your brief personally", "You get the finished video", "We help by hand if something breaks", "In exchange — honest feedback"], highlight: true },
        { name: "Creator", price: "In testing", note: "Planned", items: ["Unlimited videos in the light mode", "A monthly allowance of premium seconds", "Project history", "Vertical and horizontal formats"] },
        { name: "Agency", price: "In testing", note: "Planned", items: ["Bring your own provider key", "Batch generation", "Brand kit and presets", "Localisation into other languages"] },
      ],
      footnote:
        "Why there is no price yet: the cost of one video is driven almost entirely by premium video seconds, and that number is only known after a few dozen real runs. Publishing a price before measuring would be a guess, not an offer.",
    },
    blog: {
      kicker: "Blog",
      title: "Build log",
      sub: "What actually changed, with dates. No announcements of things that do not exist yet.",
      posts: [
        { date: "6 Sep 2026", title: "The engine audit that changed the plan", text: "We opened the old engine archive and measured it: 162 Python files, 46 KB of code in total, and not a single call that launches FFmpeg — meaning it never produced a video file. The working pipeline turned out to be a different, newer codebase. The plan was rewritten around it the same day." },
        { date: "6 Sep 2026", title: "Master Bible 2.0", text: "Readiness percentages were replaced with gates: a gate is either passed with an artefact or it is not. New sections appeared that had been missing entirely — provider licences, rights to the result, and how money comes in and out." },
        { date: "5 Sep 2026", title: "This site went live", text: "The first public artefact of the project. Built and deployed in one session." },
      ],
    },
    faq: {
      kicker: "FAQ",
      title: "The short answers",
      items: [
        { q: "How long does a generation take?", a: "Usually a few minutes: the system writes the script, generates the frames and the voice, then assembles the edit. Not instant — but it is the only wait, instead of several hours of manual work." },
        { q: "Do I need editing skills?", a: "No. No editor, no codecs, no terminal commands. You describe the video in words and receive a finished file." },
        { q: "How is this different from Runway or Sora?", a: "Those give you a single clip a few seconds long. Horsteppe is responsible for the whole video: the story, the order of scenes, voice, subtitles and the edit — and it decides which models to use along the way." },
        { q: "Which languages can the video speak?", a: "During early access it is English and Russian. Other languages are added on request — voice and subtitles support them technically, but we do not call a language ready until we have checked it on real videos." },
        { q: "Who owns the result?", a: "The video is yours. Generation relies on third-party models with their own terms, so for commercial use we walk through the details with you during early access." },
        { q: "Can I pay and use it already?", a: "We onboard one user at a time and work with the first customers by hand: we take the brief, generate, show the result and record honestly what worked and what did not." },
      ],
    },
    cta: {
      title: "Tell us what video you need",
      sub: "We will take your brief by hand and show you what the system produces on a real task.",
      button: "Get in touch",
      alt: "We reply within a day.",
    },
    footer: {
      tagline: "An AI director and editor. From an idea to the final cut.",
      rights: "All rights reserved.",
      contact: "Contact",
      orda: "Startup Orda 2 participant",
      lang: "Language",
    },
    waitlist: {
      subject: "Horsteppe — early access",
      body: "Hi!\n\nI would like to try Horsteppe.\n\nThe video I need: \nLength: \nPlatform (YouTube / Instagram / TikTok / other): \nLanguage: \n\nThank you!",
    },
    searchUi: { placeholder: "Search the page…", empty: "Nothing found", close: "Close" },
  },

  ru: {
    nav: { home: "Главная", product: "Продукт", team: "Команда", pricing: "Тарифы", blog: "Журнал", search: "Поиск" },
    hero: {
      title: "Оркестровка степи.",
      sub1: "Конвейер, который направляет ИИ",
      sub2: "на создание вашего видеошедевра.",
      cta: "Узнать больше",
    },
    problem: {
      kicker: "Проблема",
      title: "Готовый ролик сегодня — это семь вкладок и три часа",
      beforeTitle: "Как это делают сейчас",
      beforeItems: [
        "LLM, чтобы написать сценарий",
        "Генератор изображений для кадров",
        "Runway / Kling / Veo для движения",
        "ElevenLabs для озвучки",
        "Поиск музыки без проблем с правами",
        "CapCut или Premiere для монтажа",
        "Отдельный сервис для субтитров",
        "И всё это нужно свести и экспортировать",
      ],
      beforeFooter:
        "Каждый шаг — свой аккаунт, свой формат файлов и свои деньги. Плюс нужно уметь монтировать.",
      afterTitle: "Как это работает у нас",
      afterItems: ["Одно поле ввода", "Одна кнопка", "Готовый MP4 с озвучкой, субтитрами и музыкой"],
      afterFooter: "Мы продаём не ещё одну модель генерации. Мы убираем сам процесс.",
    },
    how: {
      kicker: "Как работает",
      title: "Шесть шагов, которые система проходит сама",
      sub: "Ровно тот путь, который обычно проходит небольшая продакшн-команда — только автоматически.",
      steps: [
        { n: "01", title: "Понимает задачу", text: "Разбирает вашу фразу: формат, длительность, тон, площадку и то, какой результат вам на самом деле нужен." },
        { n: "02", title: "Пишет историю", text: "Строит сценарий с сильным началом, развитием, кульминацией и внятным финалом — а не набор красивых кадров." },
        { n: "03", title: "Озвучивает", text: "Синтезирует голос первым, чтобы длительность каждой сцены задавала реальная озвучка, а не запрошенное число секунд." },
        { n: "04", title: "Планирует и снимает сцены", text: "Раскладывает историю на кадры и генерирует их, удерживая единый визуальный стиль всего ролика." },
        { n: "05", title: "Добавляет движение", text: "Оживляет каждый кадр управляемым движением камеры, а на дорогую AI-генерацию тратится только там, где движение действительно работает." },
        { n: "06", title: "Монтирует и отдаёт", text: "Собирает таймлайн, добавляет субтитры и музыку, сводит звук и выгружает готовый MP4." },
      ],
    },
    budget: {
      kicker: "Ключевая идея",
      title: "Не каждая секунда стоит одинаково",
      sub: "Дорогая AI-видеогенерация оправдана только там, где движение действительно работает на кадр. Остальное снимается управляемым движением камеры по сгенерированному изображению. Зритель разницы почти не замечает — а себестоимость ролика падает в разы.",
      exampleLabel: "Пример распределения для 60-секундного ролика",
      premium: "Премиум AI-видео",
      motion: "Движение по кадру",
      scenes: [
        { n: 1, kind: "motion", label: "Завязка" },
        { n: 2, kind: "motion", label: "Развитие" },
        { n: 3, kind: "premium", label: "Ключевой момент" },
        { n: 4, kind: "motion", label: "Переход" },
        { n: 5, kind: "premium", label: "Кульминация" },
      ],
      barNaiveLabel: "Генерировать все 60 секунд дорогой моделью",
      barSmartLabel: "Horsteppe: премиум только там, где он виден",
      footnote:
        "Схема на иллюстрации — пример логики планировщика, а не гарантированный результат конкретного ролика. Реальное распределение система считает под каждую историю отдельно.",
    },
    features: {
      kicker: "Что внутри",
      title: "Продакшн-конвейер, а не обёртка над одной моделью",
      items: [
        { title: "AI-режиссёр", text: "Отвечает за драматургию: хук, развитие, кульминацию и финал. Без этого ролик рассыпается на случайные кадры." },
        { title: "Планировщик сцен", text: "Считает тайминг и плотность закадрового текста, чтобы минутный ролик не оказался озвучен за пятнадцать секунд." },
        { title: "Умный бюджет визуала", text: "Решает, где нужна дорогая генерация видео, а где хватит движения по кадру — и держит себестоимость под контролем." },
        { title: "Повторное использование ассетов", text: "Одна и та же локация или объект переиспользуются между сценами: меньше расходов, больше связности." },
        { title: "Голос как метроном", text: "Тайминг монтажа строится по реальной длительности озвучки, а не по запрошенному числу секунд." },
        { title: "Автоматический монтаж", text: "Таймлайн, переходы, субтитры, сведение звука и финальный экспорт — без ручной работы в редакторе." },
        { title: "Независимость от провайдеров", text: "Модели подключены как заменяемые модули. Если один сервис упал или подорожал, конвейер продолжает работать." },
        { title: "Ролик доходит до конца", text: "Если премиум-генерация недоступна, сцена собирается локально. Один сбойный сервис не должен уносить весь проект." },
      ],
    },
    roadmap: {
      kicker: "Честно о состоянии",
      title: "Что уже есть и что будет дальше",
      sub: "Мы на стадии раннего доступа. Показываем реальную картину, а не список галочек.",
      columns: [
        {
          title: "Ядро конвейера", state: "В закрытом тесте",
          items: ["Идея → сценарий → сцены", "Генерация кадров", "Озвучка и тайминг по сценам", "Движение камеры по кадру", "Сборка и экспорт MP4", "Стоимость каждого платного вызова записывается", "Возобновление после сбоя"],
        },
        {
          title: "Ближайшие недели", state: "В работе",
          items: ["Субтитры, вшитые в видео", "Переходы между сценами", "Премиум AI-видео для ключевых сцен", "Живой статус генерации", "История проектов"],
        },
        {
          title: "Дальше", state: "В плане",
          items: ["Горизонтальный формат 16:9 и авторекадрирование", "Единый герой между сценами", "Правка отдельной сцены без пересборки ролика", "Анимированные субтитры для Shorts и Reels", "Локализация ролика на другие языки"],
        },
      ],
    },
    demo: {
      kicker: "Демо",
      title: "Ролик, собранный системой от начала до конца",
      sub: "Одна фраза на входе. Сценарий, кадры, голос и монтаж — без участия человека.",
      placeholder: "Демо-ролик готовится",
      caption: "Здесь появится флагманский пример. Пока он в работе — можем показать свежую версию лично.",
    },
    team: {
      kicker: "Команда",
      title: "Маленькая намеренно",
      sub: "Три роли с чёткими границами. Никто не делает всё сразу.",
      roles: [
        { role: "Основатель и продукт", who: "Амирхан", text: "Видение продукта, приоритеты, интервью с клиентами, продажи и демо. И самая трудная работа — решать, что не делать." },
        { role: "Продуктовый инженер", who: "", text: "Фронтенд, веб-интеграция, деплой и база данных. Превращает конвейер в то, чем может пользоваться человек." },
        { role: "AI-агент разработки", who: "", text: "Читает репозиторий, делает точечные задачи, гоняет тесты и чинит интеграции. Никогда не решает сам потратить деньги у провайдера или переписать архитектуру." },
      ],
      note: "Участник Startup Orda 2.",
    },
    pricing: {
      kicker: "Тарифы",
      title: "Прайса пока нет — и это осознанно",
      sub: "Сначала мы измеряем, во сколько реально обходится готовый ролик, и только потом продаём. Пока берём задачи вручную и считаем по проекту. Ниже — структура, которую проверяем.",
      tiers: [
        { name: "Ранний доступ", price: "По договорённости", note: "Доступно сейчас", items: ["Берём вашу задачу лично", "Вы получаете готовый ролик", "Помогаем руками, если что-то сломалось", "Взамен — честная обратная связь"], highlight: true },
        { name: "Creator", price: "В проверке", note: "В планах", items: ["Безлимит роликов в лёгком режиме", "Месячный пакет премиум-секунд", "История проектов", "Вертикальный и горизонтальный форматы"] },
        { name: "Agency", price: "В проверке", note: "В планах", items: ["Свой ключ провайдера", "Пакетная генерация", "Бренд-кит и пресеты", "Локализация на другие языки"] },
      ],
      footnote:
        "Почему цены ещё нет: себестоимость ролика почти целиком определяется премиум-секундами видео, а это число становится известно только после нескольких десятков реальных прогонов. Опубликовать цену до замеров — значит назвать догадку, а не предложение.",
    },
    blog: {
      kicker: "Журнал",
      title: "Что происходит на самом деле",
      sub: "Только то, что реально изменилось, с датами. Без анонсов того, чего ещё нет.",
      posts: [
        { date: "6 сентября 2026", title: "Аудит движка, который поменял план", text: "Мы открыли архив старого движка и измерили его: 162 файла, 46 КБ кода суммарно и ни одного вызова, который запускает FFmpeg — то есть видеофайл он не создавал никогда. Рабочим конвейером оказалась другая, более новая кодовая база. План переписан вокруг неё в тот же день." },
        { date: "6 сентября 2026", title: "Master Bible 2.0", text: "Проценты готовности заменены гейтами: гейт либо пройден с доказательством, либо нет. Появились разделы, которых не было вообще, — лицензии провайдеров, права на результат и то, как деньги приходят и уходят." },
        { date: "5 сентября 2026", title: "Заработал этот сайт", text: "Первый публичный артефакт проекта. Собран и опубликован за одну сессию." },
      ],
    },
    faq: {
      kicker: "Вопросы",
      title: "Коротко о главном",
      items: [
        { q: "Сколько занимает генерация?", a: "Обычно несколько минут: система последовательно пишет сценарий, генерирует кадры, озвучку и собирает монтаж. Это не мгновенно — но это единственное ожидание вместо нескольких часов ручной работы." },
        { q: "Нужно ли уметь монтировать?", a: "Нет. Никакого редактора, никаких кодеков и никаких команд в терминале. Вы описываете видео словами и получаете готовый файл." },
        { q: "Чем это отличается от Runway или Sora?", a: "Такие сервисы дают отдельный клип на несколько секунд. Horsteppe отвечает за весь ролик целиком: историю, последовательность сцен, голос, субтитры и монтаж — и сам решает, какие модели для этого использовать." },
        { q: "На каких языках может говорить ролик?", a: "На раннем доступе это русский и английский. Другие языки подключаем по запросу — озвучка и субтитры поддерживают их технически, но мы не заявляем язык готовым, пока сами не проверили его на реальных роликах." },
        { q: "Кому принадлежит результат?", a: "Ролик ваш. При этом генерация опирается на сторонние модели со своими условиями использования — для коммерческих задач мы проговариваем это отдельно на этапе раннего доступа." },
        { q: "Можно ли уже платить и пользоваться?", a: "Мы открываем доступ по одному и работаем с первыми пользователями вручную: берём задачу, генерируем, показываем результат и честно фиксируем, что получилось, а что нет." },
      ],
    },
    cta: {
      title: "Расскажите, какой ролик вам нужен",
      sub: "Мы возьмём вашу задачу в работу вручную и покажем, что система выдаёт на реальном брифе.",
      button: "Написать нам",
      alt: "Ответим в течение дня.",
    },
    footer: {
      tagline: "AI-режиссёр и монтажёр. От идеи до финального кадра.",
      rights: "Все права защищены.",
      contact: "Связаться",
      orda: "Участник Startup Orda 2",
      lang: "Язык",
    },
    waitlist: {
      subject: "Horsteppe — ранний доступ",
      body: "Здравствуйте!\n\nХочу попробовать Horsteppe.\n\nКакой ролик мне нужен: \nДлительность: \nПлощадка (YouTube / Instagram / TikTok / другое): \nЯзык: \n\nСпасибо!",
    },
    searchUi: { placeholder: "Поиск по странице…", empty: "Ничего не найдено", close: "Закрыть" },
  },
};
