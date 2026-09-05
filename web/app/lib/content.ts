export type Lang = "ru" | "en";

export const CONTACT_EMAIL = "amirkhan17.01.10@gmail.com";

export type Dict = {
  nav: { how: string; engine: string; features: string; faq: string; cta: string };
  hero: {
    badge: string;
    title: string;
    titleAccent: string;
    sub: string;
    ctaPrimary: string;
    ctaSecondary: string;
    note: string;
    promptPlaceholder: string;
    fields: { style: string; duration: string; language: string; format: string };
    fieldValues: { style: string; duration: string; language: string; format: string };
    generate: string;
    stages: string[];
  };
  problem: {
    kicker: string;
    title: string;
    beforeTitle: string;
    beforeItems: string[];
    beforeFooter: string;
    afterTitle: string;
    afterItems: string[];
    afterFooter: string;
  };
  how: {
    kicker: string;
    title: string;
    sub: string;
    steps: { n: string; title: string; text: string }[];
  };
  budget: {
    kicker: string;
    title: string;
    sub: string;
    exampleLabel: string;
    premium: string;
    motion: string;
    scenes: { n: number; kind: "premium" | "motion"; label: string }[];
    barNaiveLabel: string;
    barSmartLabel: string;
    footnote: string;
  };
  features: { kicker: string; title: string; items: { title: string; text: string }[] };
  roadmap: {
    kicker: string;
    title: string;
    sub: string;
    columns: { title: string; state: string; items: string[] }[];
  };
  demo: { kicker: string; title: string; sub: string; placeholder: string; caption: string };
  faq: { kicker: string; title: string; items: { q: string; a: string }[] };
  cta: { title: string; sub: string; button: string; alt: string };
  footer: { tagline: string; rights: string; contact: string; orda: string };
  waitlist: {
    subject: string;
    body: string;
  };
};

export const content: Record<Lang, Dict> = {
  ru: {
    nav: {
      how: "Как работает",
      engine: "Умный бюджет",
      features: "Возможности",
      faq: "Вопросы",
      cta: "Ранний доступ",
    },
    hero: {
      badge: "Ранний доступ · открываем по одному",
      title: "Одна идея —",
      titleAccent: "готовый ролик.",
      sub: "Horsteppe — это AI-режиссёр и AI-монтажёр в одном месте. Опишите видео обычными словами: система сама напишет сценарий, разложит его на сцены, создаст визуал, озвучит, смонтирует и отдаст готовый MP4.",
      ctaPrimary: "Получить ранний доступ",
      ctaSecondary: "Как это работает",
      note: "Без монтажа, без FFmpeg, без переключения между пятью сервисами.",
      promptPlaceholder: "Кинематографичный ролик про последнего астронавта на Земле…",
      fields: { style: "Стиль", duration: "Длина", language: "Язык", format: "Формат" },
      fieldValues: {
        style: "Кинематографичный",
        duration: "60 секунд",
        language: "Русский",
        format: "16:9",
      },
      generate: "Создать видео",
      stages: [
        "Пишем историю",
        "Планируем сцены",
        "Создаём визуал",
        "Записываем голос",
        "Монтируем",
        "Рендерим",
      ],
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
      afterItems: [
        "Одно поле ввода",
        "Одна кнопка",
        "Готовый MP4 с озвучкой, субтитрами и музыкой",
      ],
      afterFooter:
        "Мы продаём не ещё одну модель генерации. Мы убираем сам процесс.",
    },
    how: {
      kicker: "Как работает",
      title: "Шесть шагов, которые система проходит сама",
      sub: "Ровно тот путь, который обычно проходит небольшая продакшн-команда — только автоматически.",
      steps: [
        {
          n: "01",
          title: "Понимает задачу",
          text: "Разбирает вашу фразу: формат, длительность, тон, площадку и то, какой результат вам на самом деле нужен.",
        },
        {
          n: "02",
          title: "Пишет историю",
          text: "Строит сценарий с сильным началом, развитием, кульминацией и внятным финалом — а не набор красивых кадров.",
        },
        {
          n: "03",
          title: "Планирует сцены",
          text: "Раскладывает историю на сцены: действие, закадровый текст, тип кадра, ракурс и тайминг каждой.",
        },
        {
          n: "04",
          title: "Создаёт визуал",
          text: "Генерирует кадры и движение, удерживая единый стиль и повторно используя уже созданные объекты и локации.",
        },
        {
          n: "05",
          title: "Озвучивает",
          text: "Синтезирует голос и подстраивает тайминг сцен под реальную длину озвучки — голос задаёт ритм всему монтажу.",
        },
        {
          n: "06",
          title: "Монтирует и отдаёт",
          text: "Собирает таймлайн, добавляет переходы, субтитры и музыку, сводит звук и выгружает готовый MP4.",
        },
      ],
    },
    budget: {
      kicker: "Ключевая идея",
      title: "Не каждая секунда стоит одинаково",
      sub: "Дорогая AI-видеогенерация оправдана только там, где движение действительно работает на кадр. Остальное Horsteppe снимает управляемым движением камеры по сгенерированному изображению. Зритель разницы почти не замечает — а себестоимость ролика падает в разы.",
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
        {
          title: "AI-режиссёр",
          text: "Отвечает за драматургию: хук, развитие, кульминацию и финал. Без этого ролик рассыпается на случайные кадры.",
        },
        {
          title: "Планировщик сцен",
          text: "Считает тайминг и плотность закадрового текста, чтобы минутный ролик не оказался озвучен за пятнадцать секунд.",
        },
        {
          title: "Умный бюджет визуала",
          text: "Решает, где нужна дорогая генерация видео, а где хватит движения по кадру — и держит себестоимость под контролем.",
        },
        {
          title: "Повторное использование ассетов",
          text: "Одна и та же локация или объект переиспользуются между сценами: меньше расходов, больше связности.",
        },
        {
          title: "Голос как метроном",
          text: "Тайминг монтажа строится по реальной длительности озвучки, а не по запрошенным «60 секундам».",
        },
        {
          title: "Автоматический монтаж",
          text: "Таймлайн, переходы, субтитры, сведение звука и финальный экспорт — без ручной работы в редакторе.",
        },
        {
          title: "Независимость от провайдеров",
          text: "Модели подключены как заменяемые модули. Если один сервис упал или подорожал, конвейер продолжает работать.",
        },
        {
          title: "Ролик доходит до конца",
          text: "Если премиум-генерация недоступна, сцена собирается локально. Один сбойный сервис не должен уносить весь проект.",
        },
      ],
    },
    roadmap: {
      kicker: "Честно о состоянии",
      title: "Что уже есть и что будет дальше",
      sub: "Мы на стадии раннего доступа. Показываем реальную картину, а не список галочек.",
      columns: [
        {
          title: "Ядро конвейера",
          state: "В закрытом тесте",
          items: [
            "Идея → сценарий → сцены",
            "Генерация кадров и промптов",
            "Локальное движение по кадру",
            "Премиум AI-видео для ключевых сцен",
            "Озвучка и синхронизация тайминга",
            "Субтитры, переходы, сведение звука",
            "Финальный экспорт MP4",
          ],
        },
        {
          title: "Ближайшие недели",
          state: "В работе",
          items: [
            "Веб-интерфейс и статус генерации",
            "История проектов",
            "Изоляция проектов и докачка после сбоя",
            "Учёт себестоимости каждой генерации",
          ],
        },
        {
          title: "Дальше",
          state: "В плане",
          items: [
            "Вертикальный формат 9:16 и авторекадрирование",
            "Единый герой между сценами",
            "Правка отдельной сцены без пересборки ролика",
            "Анимированные субтитры для Shorts и Reels",
            "Локализация ролика на другие языки",
          ],
        },
      ],
    },
    demo: {
      kicker: "Демо",
      title: "Ролик, собранный системой от начала до конца",
      sub: "Одна фраза на входе. Сценарий, кадры, голос, субтитры и монтаж — без участия человека.",
      placeholder: "Демо-ролик готовится",
      caption:
        "Здесь появится флагманский пример. Пока он в работе — можем показать свежую версию лично.",
    },
    faq: {
      kicker: "Вопросы",
      title: "Коротко о главном",
      items: [
        {
          q: "Сколько занимает генерация?",
          a: "Обычно несколько минут: система последовательно пишет сценарий, генерирует кадры, озвучку и собирает монтаж. Это не мгновенно — но это единственное ожидание вместо нескольких часов ручной работы.",
        },
        {
          q: "Нужно ли уметь монтировать?",
          a: "Нет. Никакого редактора, никаких кодеков и никаких команд в терминале. Вы описываете видео словами и получаете готовый файл.",
        },
        {
          q: "Чем это отличается от Runway или Sora?",
          a: "Такие сервисы дают отдельный клип на несколько секунд. Horsteppe отвечает за весь ролик целиком: историю, последовательность сцен, голос, субтитры и монтаж — и сам решает, какие модели для этого использовать.",
        },
        {
          q: "На каких языках может говорить ролик?",
          a: "На раннем доступе это русский и английский. Другие языки подключаем по запросу — озвучка и субтитры поддерживают их технически, но мы не заявляем язык готовым, пока сами не проверили его на реальных роликах.",
        },
        {
          q: "Кому принадлежит результат?",
          a: "Ролик ваш. При этом генерация опирается на сторонние модели со своими условиями использования — для коммерческих задач мы проговариваем это отдельно на этапе раннего доступа.",
        },
        {
          q: "Можно ли уже платить и пользоваться?",
          a: "Мы открываем доступ по одному и работаем с первыми пользователями вручную: берём задачу, генерируем, показываем результат и честно фиксируем, что получилось, а что нет.",
        },
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
    },
    waitlist: {
      subject: "Horsteppe — ранний доступ",
      body: "Здравствуйте!\n\nХочу попробовать Horsteppe.\n\nКакой ролик мне нужен: \nДлительность: \nПлощадка (YouTube / Instagram / TikTok / другое): \nЯзык: \n\nСпасибо!",
    },
  },

  en: {
    nav: {
      how: "How it works",
      engine: "Smart budget",
      features: "Capabilities",
      faq: "FAQ",
      cta: "Early access",
    },
    hero: {
      badge: "Early access · onboarding one by one",
      title: "One idea —",
      titleAccent: "a finished video.",
      sub: "Horsteppe is an AI director and an AI editor in one place. Describe your video in plain words: it writes the script, breaks it into scenes, generates the visuals, records the voice, edits everything and hands you a finished MP4.",
      ctaPrimary: "Get early access",
      ctaSecondary: "See how it works",
      note: "No editing software, no FFmpeg, no juggling five different services.",
      promptPlaceholder: "A cinematic short about the last astronaut on Earth…",
      fields: { style: "Style", duration: "Length", language: "Language", format: "Format" },
      fieldValues: {
        style: "Cinematic",
        duration: "60 seconds",
        language: "English",
        format: "16:9",
      },
      generate: "Generate video",
      stages: [
        "Writing the story",
        "Planning scenes",
        "Creating visuals",
        "Recording voice",
        "Editing",
        "Rendering",
      ],
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
      afterItems: [
        "One input field",
        "One button",
        "A finished MP4 with voice, subtitles and music",
      ],
      afterFooter:
        "We are not selling one more generation model. We are removing the workflow itself.",
    },
    how: {
      kicker: "How it works",
      title: "Six steps the system takes on its own",
      sub: "Exactly the path a small production team would follow — only automatically.",
      steps: [
        {
          n: "01",
          title: "Understands the brief",
          text: "Reads your sentence: format, length, tone, platform, and what result you actually need.",
        },
        {
          n: "02",
          title: "Writes the story",
          text: "Builds a script with a strong hook, escalation, a climax and a clear ending — not a pile of pretty frames.",
        },
        {
          n: "03",
          title: "Plans the scenes",
          text: "Breaks the story into scenes: action, narration, shot type, framing and the timing of each one.",
        },
        {
          n: "04",
          title: "Creates the visuals",
          text: "Generates frames and motion while holding one visual style and reusing locations and objects it already made.",
        },
        {
          n: "05",
          title: "Records the voice",
          text: "Synthesises narration and retimes the scenes to the real length of the audio — the voice drives the edit.",
        },
        {
          n: "06",
          title: "Edits and delivers",
          text: "Assembles the timeline, adds transitions, subtitles and music, mixes the audio and exports a finished MP4.",
        },
      ],
    },
    budget: {
      kicker: "The core idea",
      title: "Not every second is worth the same",
      sub: "Expensive AI video generation only pays off where motion genuinely carries the shot. Everything else Horsteppe shoots as controlled camera movement over a generated frame. Viewers barely notice the difference — the cost per video drops several times over.",
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
        {
          title: "AI director",
          text: "Owns the dramaturgy: hook, escalation, climax and ending. Without it a video falls apart into random shots.",
        },
        {
          title: "Scene planner",
          text: "Computes timing and narration density so a one-minute video does not end up voiced in fifteen seconds.",
        },
        {
          title: "Smart visual budget",
          text: "Decides where expensive video generation is worth it and where camera motion is enough — keeping cost under control.",
        },
        {
          title: "Asset reuse",
          text: "The same location or object is reused across scenes: less spend, more visual continuity.",
        },
        {
          title: "Voice as the metronome",
          text: "The edit is timed to the real duration of the narration, not to a requested “60 seconds”.",
        },
        {
          title: "Automatic editing",
          text: "Timeline, transitions, subtitles, audio mix and final export — with no manual work in an editor.",
        },
        {
          title: "Provider independence",
          text: "Models are plugged in as replaceable modules. If one service goes down or gets expensive, the pipeline keeps running.",
        },
        {
          title: "The video always finishes",
          text: "If premium generation is unavailable, the scene is rendered locally. One failing service must not kill the project.",
        },
      ],
    },
    roadmap: {
      kicker: "Where we honestly are",
      title: "What exists today and what comes next",
      sub: "We are at the early-access stage. This is the real picture, not a checkbox list.",
      columns: [
        {
          title: "Pipeline core",
          state: "In closed testing",
          items: [
            "Idea → script → scenes",
            "Frame and prompt generation",
            "Local camera motion",
            "Premium AI video for key scenes",
            "Voice and timing synchronisation",
            "Subtitles, transitions, audio mix",
            "Final MP4 export",
          ],
        },
        {
          title: "Next few weeks",
          state: "In progress",
          items: [
            "Web interface and live generation status",
            "Project history",
            "Project isolation and resume after failure",
            "Per-generation cost tracking",
          ],
        },
        {
          title: "After that",
          state: "Planned",
          items: [
            "Vertical 9:16 and automatic reframing",
            "One consistent character across scenes",
            "Editing a single scene without a full re-render",
            "Animated captions for Shorts and Reels",
            "Localising a video into other languages",
          ],
        },
      ],
    },
    demo: {
      kicker: "Demo",
      title: "A video assembled by the system end to end",
      sub: "One sentence in. Script, frames, voice, subtitles and the edit — with no human in the loop.",
      placeholder: "Demo video in production",
      caption:
        "The flagship example will live here. While it is being finished, we are happy to show the latest cut in person.",
    },
    faq: {
      kicker: "FAQ",
      title: "The short answers",
      items: [
        {
          q: "How long does a generation take?",
          a: "Usually a few minutes: the system writes the script, generates the frames and the voice, then assembles the edit. Not instant — but it is the only wait, instead of several hours of manual work.",
        },
        {
          q: "Do I need editing skills?",
          a: "No. No editor, no codecs, no terminal commands. You describe the video in words and receive a finished file.",
        },
        {
          q: "How is this different from Runway or Sora?",
          a: "Those give you a single clip a few seconds long. Horsteppe is responsible for the whole video: the story, the order of scenes, voice, subtitles and the edit — and it decides which models to use along the way.",
        },
        {
          q: "Which languages can the video speak?",
          a: "During early access it is English and Russian. Other languages are added on request — voice and subtitles support them technically, but we do not call a language ready until we have checked it on real videos.",
        },
        {
          q: "Who owns the result?",
          a: "The video is yours. Generation relies on third-party models with their own terms, so for commercial use we walk through the details with you during early access.",
        },
        {
          q: "Can I pay and use it already?",
          a: "We onboard one user at a time and work with the first customers by hand: we take the brief, generate, show the result and record honestly what worked and what did not.",
        },
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
    },
    waitlist: {
      subject: "Horsteppe — early access",
      body: "Hi!\n\nI would like to try Horsteppe.\n\nThe video I need: \nLength: \nPlatform (YouTube / Instagram / TikTok / other): \nLanguage: \n\nThank you!",
    },
  },
};
