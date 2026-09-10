import type { Lang } from "./i18n";

/**
 * Юридические документы и справка.
 *
 * Тексты описывают то, что происходит в продукте на самом деле: какие сервисы
 * получают данные, что хранится и на что человек имеет право. Шаблон из
 * интернета сюда не годится — у него другой список субпроцессоров и другие
 * обещания, а отвечать придётся за эти.
 *
 * Перед публичным платным запуском документы должен посмотреть юрист:
 * здесь описан ранний доступ без юридического лица.
 */
export type Section = { h: string; p: string[] };
export type Doc = { title: string; updated: string; intro: string; sections: Section[] };

export type LegalDoc = "privacy" | "terms" | "cookies" | "help";

export type LegalDict = {
  nav: Record<LegalDoc, string>;
  updatedLabel: string;
  contactNote: string;
  docs: Record<LegalDoc, Doc>;
};

const UPDATED = "2026-09-10";

export const legal: Record<Lang, LegalDict> = {
  en: {
    nav: { privacy: "Privacy", terms: "Terms", cookies: "Cookies", help: "Help center" },
    updatedLabel: "Last updated",
    contactNote: "Questions about any of this go to",
    docs: {
      privacy: {
        title: "Privacy Policy",
        updated: UPDATED,
        intro:
          "Horsteppe turns a text prompt into a finished video. To do that it stores a small amount of data about you and sends your prompt to third-party AI services. This page says exactly what and to whom.",
        sections: [
          {
            h: "What we store",
            p: [
              "Your email address and an authentication record, so you can sign in and find your projects.",
              "The prompts you write and the settings you choose — style, length, format.",
              "The videos, frames, voice tracks and subtitles produced for you.",
              "A cost record for each paid step, so we can measure what a video costs to make.",
            ],
          },
          {
            h: "What we do not store",
            p: [
              "We never see or store your password: authentication is handled by Supabase.",
              "We do not run analytics, advertising or tracking scripts. There is no third-party pixel on this site.",
              "We do not sell data to anyone, and there is nobody we could sell it to — this is an early-access project, not an ad business.",
            ],
          },
          {
            h: "Who else receives your data",
            p: [
              "Your prompt is sent to the AI services that produce the video. Each of them has its own privacy policy, and we cannot control what they do beyond their published terms.",
              "Supabase — database, file storage and sign-in. Vercel — website hosting. OpenRouter — writes the script. ElevenLabs — generates the voice. fal.ai and Pollinations — generate the frames. GitHub — runs the production worker.",
              "We do not send your email address to any of the AI services. They receive the prompt text only.",
            ],
          },
          {
            h: "How long we keep it",
            p: [
              "Projects and generated files are kept until you ask us to delete them. There is no automatic expiry yet.",
              "Write to us and we will delete your account, your projects and every generated file. We do this by hand and confirm when it is done.",
            ],
          },
          {
            h: "Where the data lives",
            p: [
              "In Supabase and Vercel infrastructure. The AI services process prompts on their own servers, which may be outside your country.",
              "If cross-border processing matters for your work, tell us before you upload anything sensitive.",
            ],
          },
          {
            h: "Your rights",
            p: [
              "You can ask what we hold about you, ask for a copy, ask for corrections, or ask for deletion.",
              "There is no self-service dashboard for this yet — every request is handled by a person, by email.",
            ],
          },
          {
            h: "Children",
            p: ["Horsteppe is not intended for people under 18."],
          },
          {
            h: "Changes",
            p: [
              "When this page changes, the date at the top changes with it. During early access it will change more often than we would like — the product is still taking shape.",
            ],
          },
        ],
      },

      terms: {
        title: "Terms of Service",
        updated: UPDATED,
        intro:
          "Plain terms for an early-access product. If something here is unclear or unfair for your case, write to us — at this stage we can actually talk.",
        sections: [
          {
            h: "What Horsteppe is right now",
            p: [
              "An early-access product. It works, and it also breaks: a provider can go down mid-production and a video can fail. We show the real state instead of hiding it.",
              "There is no uptime guarantee, no support hours and no service level agreement.",
            ],
          },
          {
            h: "Who owns the videos",
            p: [
              "The videos you make are yours. We do not claim ownership of them.",
              "But your rights cannot exceed what the underlying AI models allow. Each generated frame, voice track and script comes from a third-party model with its own licence, and those licences differ.",
              "For commercial use we agree the details with you individually during early access. Ask before you publish a paid campaign — it takes one message and avoids a real problem.",
            ],
          },
          {
            h: "What you may not generate",
            p: [
              "Anything illegal where you are, or where we are.",
              "Content that impersonates a real person, imitates a real organisation, or passes off generated material as a genuine record.",
              "Sexual content involving minors, incitement to violence, or targeted harassment of a private individual.",
              "We may refuse a request or remove a project that falls into these, and we will say why.",
            ],
          },
          {
            h: "Your account",
            p: [
              "One person, one account. Keep your password to yourself.",
              "Limits protect the generation budget: a set number of videos per day and one in production at a time. They may change without notice while we measure real costs.",
            ],
          },
          {
            h: "Money",
            p: [
              "Early access is free. There is no price list because we have not finished measuring what a finished video actually costs.",
              "When paid plans appear, nothing starts charging you automatically. You will be asked first.",
            ],
          },
          {
            h: "Liability",
            p: [
              "Horsteppe is provided as is. We are not liable for lost profit, lost time or consequences of publishing a generated video.",
              "This is not a disclaimer meant to sound scary — it reflects what an early-access project can honestly promise.",
            ],
          },
          {
            h: "Ending it",
            p: [
              "You can stop using Horsteppe at any time and ask us to delete everything.",
              "We may close an account that breaks these terms, and we will explain the reason.",
            ],
          },
          {
            h: "Changes",
            p: [
              "These terms will change as the product grows up. Material changes will be announced by email to registered users.",
            ],
          },
        ],
      },

      cookies: {
        title: "Cookie Notice",
        updated: UPDATED,
        intro:
          "Short, because there is little to say: Horsteppe uses two cookies and neither of them tracks you.",
        sections: [
          {
            h: "The sign-in cookie",
            p: [
              "Set by Supabase after you sign in, so the site knows it is you on the next page. Without it you would be signed out on every click.",
              "It disappears when you sign out.",
            ],
          },
          {
            h: "The language cookie",
            p: [
              "Remembers whether you chose English, Russian or Kazakh, so the site opens in the same language next time.",
              "It stores three letters and nothing else.",
            ],
          },
          {
            h: "What is not here",
            p: [
              "No analytics, no advertising, no third-party trackers, no fingerprinting. Nothing is shared with an ad network, because we do not work with any.",
              "This is why there is no cookie consent banner: there is nothing to consent to beyond what makes the site function.",
            ],
          },
          {
            h: "Turning them off",
            p: [
              "You can block cookies in your browser. The language choice will simply stop being remembered, and signing in will stop working — the sign-in cookie is what keeps you signed in.",
            ],
          },
        ],
      },

      help: {
        title: "Help center",
        updated: UPDATED,
        intro: "The questions people actually ask. If yours is not here, write to us — a person answers.",
        sections: [
          {
            h: "How long does a video take?",
            p: [
              "A few minutes when everything is available. You can close the page: the project keeps going and waits for you on the My videos page.",
            ],
          },
          {
            h: "Why did my video fail?",
            p: [
              "Almost always because an AI provider was unavailable at that moment. The project page shows the reason in plain words.",
              "The script and the voice are saved, so a retry does not pay for them twice.",
            ],
          },
          {
            h: "Why can I only make one video at a time?",
            p: [
              "Generation costs real money at every step. A limit of one in production and a few per day is what keeps an accidental loop from emptying the budget.",
            ],
          },
          {
            h: "Can I choose the AI model?",
            p: [
              "No, and that is deliberate. Choosing between models is our job, not yours — you choose the result you want.",
            ],
          },
          {
            h: "Can I use the video commercially?",
            p: [
              "Ask us first. The answer depends on which models produced your frames and voice, and those licences differ. During early access we check it per project.",
            ],
          },
          {
            h: "How do I delete everything?",
            p: [
              "Write to us and say so. We delete the account, the projects and every generated file, and confirm when it is done.",
            ],
          },
        ],
      },
    },
  },

  ru: {
    nav: { privacy: "Конфиденциальность", terms: "Условия", cookies: "Cookie", help: "Справка" },
    updatedLabel: "Обновлено",
    contactNote: "Вопросы по любому из этого —",
    docs: {
      privacy: {
        title: "Политика конфиденциальности",
        updated: UPDATED,
        intro:
          "Horsteppe превращает текстовый запрос в готовый ролик. Для этого он хранит немного данных о вас и передаёт ваш запрос сторонним AI-сервисам. Здесь написано, что именно и кому.",
        sections: [
          {
            h: "Что мы храним",
            p: [
              "Вашу почту и запись для входа, чтобы вы могли войти и найти свои проекты.",
              "Запросы, которые вы пишете, и выбранные настройки — стиль, длину, формат.",
              "Готовые ролики, кадры, озвучку и субтитры.",
              "Запись о стоимости каждого платного шага, чтобы понимать себестоимость ролика.",
            ],
          },
          {
            h: "Чего мы не храним",
            p: [
              "Мы не видим и не храним ваш пароль: вход обрабатывает Supabase.",
              "У нас нет аналитики, рекламы и следящих скриптов. На сайте нет ни одного стороннего пикселя.",
              "Мы никому не продаём данные, и продавать их некому — это проект раннего доступа, а не рекламный бизнес.",
            ],
          },
          {
            h: "Кто ещё получает ваши данные",
            p: [
              "Ваш запрос уходит тем AI-сервисам, которые делают ролик. У каждого своя политика, и мы не можем повлиять на них дальше их же опубликованных условий.",
              "Supabase — база, хранилище файлов и вход. Vercel — хостинг сайта. OpenRouter — пишет сценарий. ElevenLabs — делает голос. fal.ai и Pollinations — рисуют кадры. GitHub — запускает сборщик.",
              "Вашу почту мы не передаём ни одному AI-сервису. Им уходит только текст запроса.",
            ],
          },
          {
            h: "Сколько это хранится",
            p: [
              "Проекты и файлы хранятся, пока вы не попросите их удалить. Автоматического срока пока нет.",
              "Напишите нам — удалим аккаунт, проекты и все созданные файлы. Делаем это руками и подтверждаем, когда закончили.",
            ],
          },
          {
            h: "Где лежат данные",
            p: [
              "В инфраструктуре Supabase и Vercel. AI-сервисы обрабатывают запросы на своих серверах, которые могут находиться за пределами вашей страны.",
              "Если для вашей работы важна страна обработки — скажите заранее, до того как загрузите что-то чувствительное.",
            ],
          },
          {
            h: "Ваши права",
            p: [
              "Вы можете узнать, что мы о вас храним, попросить копию, исправление или удаление.",
              "Отдельного раздела для этого пока нет — каждый запрос обрабатывает человек, по почте.",
            ],
          },
          {
            h: "Возраст",
            p: ["Horsteppe не предназначен для людей младше 18 лет."],
          },
          {
            h: "Изменения",
            p: [
              "Когда эта страница меняется, меняется и дата наверху. На раннем доступе она будет меняться чаще, чем хотелось бы: продукт ещё формируется.",
            ],
          },
        ],
      },

      terms: {
        title: "Условия использования",
        updated: UPDATED,
        intro:
          "Простые условия для продукта на раннем доступе. Если что-то здесь непонятно или несправедливо для вашего случая — напишите: на этом этапе с нами ещё можно договориться.",
        sections: [
          {
            h: "Что такое Horsteppe сейчас",
            p: [
              "Продукт раннего доступа. Он работает — и он ломается: провайдер может отказать посреди сборки, и ролик не получится. Мы показываем реальное состояние, а не прячем его.",
              "Гарантий доступности, часов поддержки и соглашения об уровне сервиса нет.",
            ],
          },
          {
            h: "Кому принадлежат ролики",
            p: [
              "Сделанные вами ролики — ваши. Мы не претендуем на них.",
              "Но ваши права не могут быть шире того, что разрешают сами AI-модели. Каждый кадр, голос и сценарий приходит от стороннего сервиса со своей лицензией, и лицензии эти разные.",
              "Коммерческое использование мы согласуем с вами отдельно на раннем доступе. Спросите до запуска платной кампании — это одно сообщение, которое избавляет от настоящей проблемы.",
            ],
          },
          {
            h: "Чего нельзя создавать",
            p: [
              "Ничего противозаконного — ни у вас, ни у нас.",
              "Материалы, выдающие себя за реального человека, подражающие реальной организации или подающие сгенерированное как подлинную запись.",
              "Сексуальный контент с участием несовершеннолетних, призывы к насилию, травлю конкретного человека.",
              "Мы можем отказать в запросе или удалить проект, попадающий под это, и объясним причину.",
            ],
          },
          {
            h: "Ваш аккаунт",
            p: [
              "Один человек — один аккаунт. Пароль держите при себе.",
              "Лимиты защищают бюджет генерации: несколько роликов в сутки и один в работе одновременно. Они могут меняться без предупреждения, пока мы измеряем реальную себестоимость.",
            ],
          },
          {
            h: "Деньги",
            p: [
              "Ранний доступ бесплатный. Прайса нет, потому что мы ещё не досчитали, во сколько обходится готовый ролик.",
              "Когда появятся платные планы, ничего не начнёт списываться само. Сначала спросим.",
            ],
          },
          {
            h: "Ответственность",
            p: [
              "Horsteppe предоставляется как есть. Мы не отвечаем за упущенную выгоду, потерянное время и последствия публикации сгенерированного ролика.",
              "Это не попытка напугать формулировкой — это честная граница того, что может обещать проект на раннем доступе.",
            ],
          },
          {
            h: "Прекращение",
            p: [
              "Вы можете перестать пользоваться Horsteppe в любой момент и попросить всё удалить.",
              "Мы можем закрыть аккаунт, нарушающий эти условия, и объясним причину.",
            ],
          },
          {
            h: "Изменения",
            p: [
              "Условия будут меняться по мере взросления продукта. О существенных изменениях сообщим зарегистрированным пользователям по почте.",
            ],
          },
        ],
      },

      cookies: {
        title: "О файлах cookie",
        updated: UPDATED,
        intro: "Коротко, потому что рассказывать почти нечего: Horsteppe использует две cookie, и ни одна не следит за вами.",
        sections: [
          {
            h: "Cookie входа",
            p: [
              "Её ставит Supabase после входа, чтобы сайт узнавал вас на следующей странице. Без неё вы выходили бы из аккаунта на каждом клике.",
              "Исчезает, когда вы выходите.",
            ],
          },
          {
            h: "Cookie языка",
            p: [
              "Запоминает, выбрали вы русский, английский или казахский, чтобы сайт открылся на том же языке.",
              "Хранит три буквы и больше ничего.",
            ],
          },
          {
            h: "Чего здесь нет",
            p: [
              "Ни аналитики, ни рекламы, ни сторонних трекеров, ни отпечатков браузера. Ничего не уходит в рекламные сети, потому что мы с ними не работаем.",
              "Поэтому здесь нет и баннера про cookie: соглашаться не с чем, кроме того, без чего сайт не работает.",
            ],
          },
          {
            h: "Как их отключить",
            p: [
              "Cookie можно заблокировать в браузере. Тогда выбор языка просто перестанет запоминаться, а вход перестанет работать — именно cookie входа и держит вас в аккаунте.",
            ],
          },
        ],
      },

      help: {
        title: "Справка",
        updated: UPDATED,
        intro: "Вопросы, которые задают на самом деле. Если вашего здесь нет — напишите, отвечает человек.",
        sections: [
          {
            h: "Сколько занимает сборка ролика?",
            p: [
              "Несколько минут, когда всё доступно. Страницу можно закрыть: проект продолжит собираться и будет ждать вас в разделе «Мои видео».",
            ],
          },
          {
            h: "Почему ролик не получился?",
            p: [
              "Почти всегда потому, что AI-провайдер оказался недоступен в этот момент. На странице проекта причина написана словами.",
              "Сценарий и озвучка сохраняются, поэтому повтор не оплачивает их заново.",
            ],
          },
          {
            h: "Почему можно делать только один ролик за раз?",
            p: [
              "Генерация стоит настоящих денег на каждом шаге. Ограничение в один ролик в работе и несколько в сутки не даёт случайному циклу опустошить бюджет.",
            ],
          },
          {
            h: "Можно выбрать модель?",
            p: [
              "Нет, и это осознанно. Выбирать между моделями — наша работа, а не ваша. Вы выбираете нужный результат.",
            ],
          },
          {
            h: "Можно использовать ролик коммерчески?",
            p: [
              "Спросите сначала нас. Ответ зависит от того, какие модели сделали ваши кадры и голос, а лицензии у них разные. На раннем доступе мы проверяем это по каждому проекту.",
            ],
          },
          {
            h: "Как удалить всё?",
            p: [
              "Напишите нам об этом. Удалим аккаунт, проекты и все созданные файлы, и подтвердим, когда закончим.",
            ],
          },
        ],
      },
    },
  },

  kk: {
    nav: { privacy: "Құпиялылық", terms: "Шарттар", cookies: "Cookie", help: "Анықтама" },
    updatedLabel: "Жаңартылды",
    contactNote: "Осының бәрі бойынша сұрақтар —",
    docs: {
      privacy: {
        title: "Құпиялылық саясаты",
        updated: UPDATED,
        intro:
          "Horsteppe мәтіндік сұранысты дайын роликке айналдырады. Ол үшін ол сіз туралы аз ғана дерек сақтайды және сұранысыңызды сыртқы AI-сервистерге жібереді. Мұнда нақты нені және кімге екені жазылған.",
        sections: [
          {
            h: "Не сақтаймыз",
            p: [
              "Поштаңызды және кіру жазбасын — кіріп, жобаларыңызды табу үшін.",
              "Жазған сұраныстарыңызды және таңдаған баптауларыңызды: стиль, ұзақтық, пішім.",
              "Дайын роликтерді, кадрларды, дауысты және субтитрлерді.",
              "Әр ақылы қадамның құны туралы жазбаны — роликтің өзіндік құнын түсіну үшін.",
            ],
          },
          {
            h: "Нені сақтамаймыз",
            p: [
              "Құпиясөзіңізді көрмейміз және сақтамаймыз: кіруді Supabase өңдейді.",
              "Бізде аналитика, жарнама және бақылау скрипттері жоқ. Сайтта бірде-бір сыртқы пиксель жоқ.",
              "Деректерді ешкімге сатпаймыз, әрі сатуға да ешкім жоқ — бұл ерте қолжетімділік жобасы, жарнама бизнесі емес.",
            ],
          },
          {
            h: "Деректеріңізді тағы кім алады",
            p: [
              "Сұранысыңыз роликті жасайтын AI-сервистерге барады. Әрқайсысының өз саясаты бар, және біз оларға жарияланған шарттарынан әрі ықпал ете алмаймыз.",
              "Supabase — дерекқор, файл қоймасы және кіру. Vercel — сайт хостингі. OpenRouter — сценарий жазады. ElevenLabs — дауыс жасайды. fal.ai және Pollinations — кадр салады. GitHub — жинақтаушыны іске қосады.",
              "Поштаңызды бірде-бір AI-сервиске бермейміз. Оларға тек сұраныс мәтіні барады.",
            ],
          },
          {
            h: "Қанша уақыт сақталады",
            p: [
              "Жобалар мен файлдар сіз жоюды сұрағанша сақталады. Автоматты мерзім әзірге жоқ.",
              "Бізге жазыңыз — аккаунтты, жобаларды және барлық жасалған файлды жоямыз. Мұны қолмен істейміз және аяқтағанда растаймыз.",
            ],
          },
          {
            h: "Деректер қайда тұрады",
            p: [
              "Supabase және Vercel инфрақұрылымында. AI-сервистер сұраныстарды өз серверлерінде өңдейді, олар сіздің елден тыс болуы мүмкін.",
              "Егер жұмысыңыз үшін өңдеу елі маңызды болса — құпия нәрсе жүктемес бұрын алдын ала айтыңыз.",
            ],
          },
          {
            h: "Сіздің құқығыңыз",
            p: [
              "Біз сіз туралы не сақтайтынымызды сұрай аласыз, көшірмесін, түзетуін немесе жоюын талап ете аласыз.",
              "Бұған арналған бөлек бөлім әзірге жоқ — әр сұранысты адам поштамен өңдейді.",
            ],
          },
          { h: "Жас шектеуі", p: ["Horsteppe 18 жасқа толмағандарға арналмаған."] },
          {
            h: "Өзгерістер",
            p: [
              "Бұл бет өзгергенде жоғарыдағы күн де өзгереді. Ерте қолжетімділікте ол қалағаннан жиірек өзгереді: өнім әлі қалыптасып жатыр.",
            ],
          },
        ],
      },

      terms: {
        title: "Пайдалану шарттары",
        updated: UPDATED,
        intro:
          "Ерте қолжетімділіктегі өнімге арналған қарапайым шарттар. Мұнда бірдеңе түсініксіз немесе сіздің жағдайыңызға әділетсіз болса — жазыңыз: бұл кезеңде әлі келісуге болады.",
        sections: [
          {
            h: "Horsteppe қазір деген не",
            p: [
              "Ерте қолжетімділіктегі өнім. Ол жұмыс істейді — және сынады да: провайдер жинау ортасында бас тартып, ролик шықпай қалуы мүмкін. Біз нақты жағдайды көрсетеміз, жасырмаймыз.",
              "Қолжетімділік кепілі, қолдау сағаттары және қызмет деңгейі туралы келісім жоқ.",
            ],
          },
          {
            h: "Роликтер кімдікі",
            p: [
              "Сіз жасаған роликтер — сіздікі. Біз оларға таласпаймыз.",
              "Бірақ құқығыңыз AI-модельдер рұқсат еткеннен кең бола алмайды. Әр кадр, дауыс және сценарий өз лицензиясы бар сыртқы сервистен келеді, ал ол лицензиялар әртүрлі.",
              "Коммерциялық пайдалануды ерте қолжетімділікте сізбен бөлек келісеміз. Ақылы науқанды бастамас бұрын сұраңыз — бұл бір хабарлама, ол нағыз мәселеден құтқарады.",
            ],
          },
          {
            h: "Нені жасауға болмайды",
            p: [
              "Заңсыз ештеңе — сізде де, бізде де.",
              "Нақты адам болып көрінетін, нақты ұйымға еліктейтін немесе жасалғанды шынайы жазба ретінде ұсынатын материалдар.",
              "Кәмелетке толмағандар қатысатын жыныстық мазмұн, зорлыққа шақыру, нақты адамды қудалау.",
              "Осыған жататын сұраныстан бас тартуымыз немесе жобаны жоюымыз мүмкін, себебін түсіндіреміз.",
            ],
          },
          {
            h: "Сіздің аккаунтыңыз",
            p: [
              "Бір адам — бір аккаунт. Құпиясөзді өзіңізде сақтаңыз.",
              "Шектеулер генерация бюджетін қорғайды: тәулігіне бірнеше ролик және бір мезгілде біреуі жұмыста. Нақты өзіндік құнды өлшеп жатқанда олар ескертусіз өзгеруі мүмкін.",
            ],
          },
          {
            h: "Ақша",
            p: [
              "Ерте қолжетімділік тегін. Бағасы жоқ, себебі дайын ролик қанша тұратынын әлі санап бітірген жоқпыз.",
              "Ақылы жоспарлар пайда болғанда ештеңе өздігінен алынып қалмайды. Алдымен сұраймыз.",
            ],
          },
          {
            h: "Жауапкершілік",
            p: [
              "Horsteppe қалай бар, солай ұсынылады. Жіберіп алған пайда, жоғалған уақыт және жасалған роликті жариялаудың салдары үшін жауап бермейміз.",
              "Бұл қорқыту емес — ерте қолжетімділіктегі жоба адал уәде ете алатын шекара.",
            ],
          },
          {
            h: "Тоқтату",
            p: [
              "Horsteppe-ті кез келген сәтте қолдануды тоқтатып, бәрін жоюды сұрай аласыз.",
              "Осы шарттарды бұзған аккаунтты жабуымыз мүмкін, себебін түсіндіреміз.",
            ],
          },
          {
            h: "Өзгерістер",
            p: ["Өнім есейген сайын шарттар өзгереді. Елеулі өзгерістер туралы тіркелгендерге поштамен хабарлаймыз."],
          },
        ],
      },

      cookies: {
        title: "Cookie туралы",
        updated: UPDATED,
        intro: "Қысқаша, себебі айтары аз: Horsteppe екі cookie қолданады, олардың ешқайсысы сізді бақыламайды.",
        sections: [
          {
            h: "Кіру cookie",
            p: [
              "Оны кіргеннен кейін Supabase қояды, сайт келесі бетте сізді тануы үшін. Онсыз әр басқан сайын аккаунттан шығып отырар едіңіз.",
              "Шыққанда жойылады.",
            ],
          },
          {
            h: "Тіл cookie",
            p: [
              "Қазақ, орыс әлде ағылшын таңдағаныңызды есте сақтайды, сайт сол тілде ашылуы үшін.",
              "Үш әріп сақтайды, басқа ештеңе жоқ.",
            ],
          },
          {
            h: "Мұнда не жоқ",
            p: [
              "Аналитика да, жарнама да, сыртқы бақылаушылар да, браузер таңбасы да жоқ. Жарнама желілеріне ештеңе кетпейді, себебі біз олармен жұмыс істемейміз.",
              "Сондықтан cookie туралы баннер де жоқ: сайт жұмыс істеуі үшін қажеттіден басқа келісетін ештеңе жоқ.",
            ],
          },
          {
            h: "Қалай өшіруге болады",
            p: [
              "Cookie-ді браузерде бұғаттауға болады. Сонда тіл таңдауы есте сақталмайды, ал кіру істен шығады — аккаунтта ұстап тұрған дәл сол кіру cookie.",
            ],
          },
        ],
      },

      help: {
        title: "Анықтама",
        updated: UPDATED,
        intro: "Шын мәнінде қойылатын сұрақтар. Сіздікі мұнда болмаса — жазыңыз, адам жауап береді.",
        sections: [
          {
            h: "Ролик жинау қанша уақыт алады?",
            p: ["Бәрі қолжетімді болса, бірнеше минут. Бетті жабуға болады: жоба жиналуын жалғастырады және «Менің бейнелерім» бөлімінде күтеді."],
          },
          {
            h: "Ролик неге шықпады?",
            p: [
              "Әрдайым дерлік AI-провайдер сол сәтте қолжетімсіз болғандықтан. Жоба бетінде себеп сөзбен жазылған.",
              "Сценарий мен дауыс сақталады, сондықтан қайталау оларды екінші рет төлемейді.",
            ],
          },
          {
            h: "Неге бір мезгілде бір ғана ролик?",
            p: ["Генерация әр қадамда нақты ақша тұрады. Бір ролик жұмыста және тәулігіне бірнеше деген шектеу кездейсоқ цикл бюджетті босатып жібермеуі үшін керек."],
          },
          {
            h: "Модельді таңдауға бола ма?",
            p: ["Жоқ, және бұл әдейі. Модельдер арасынан таңдау — біздің жұмысымыз, сіздікі емес. Сіз қажет нәтижені таңдайсыз."],
          },
          {
            h: "Роликті коммерциялық қолдануға бола ма?",
            p: ["Алдымен бізден сұраңыз. Жауап кадрларыңыз бен дауысыңызды қай модель жасағанына байланысты, ал олардың лицензиясы әртүрлі. Ерте қолжетімділікте мұны әр жоба бойынша тексереміз."],
          },
          {
            h: "Бәрін қалай жоюға болады?",
            p: ["Бізге жазыңыз. Аккаунтты, жобаларды және барлық жасалған файлды жоямыз, аяқтағанда растаймыз."],
          },
        ],
      },
    },
  },
};
