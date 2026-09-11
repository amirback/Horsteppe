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
  /** Ошибки API приходят машинными кодами — здесь их человеческие формулировки. */
  errors: Record<string, string>;
  auth: {
    title: string;
    lead: string;
    email: string;
    password: string;
    signIn: string;
    signUp: string;
    toSignUp: string;
    toSignIn: string;
    confirm: string;
    working: string;
  };
  library: {
    title: string;
    active: string;
    done: string;
    failed: string;
    total: string;
    empty: string;
    emptyCta: string;
    open: string;
    statuses: Record<string, string>;
  };
  project: {
    back: string;
    queued: string;
    working: string;
    ready: string;
    failed: string;
    download: string;
    again: string;
    scenes: string;
    duration: string;
    retry: string;
    stages: string[];
  };
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
      "Production takes a few minutes. You can close the page and come back — the project keeps running.",
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
    errors: {
      backend_not_configured: "Generation is not connected yet — the administrator has not set up database access.",
      unauthorized: "Sign in to create a video.",
      invalid_request: "Malformed request.",
      topic_too_short: "Write a couple of sentences about the video first.",
      topic_too_long: "The description is too long — keep it under 500 characters.",
      rate_limit_concurrent: "You already have a video in production. Its progress is on the «My videos» page.",
      rate_limit_daily: "Daily limit reached. Try again tomorrow.",
      create_failed: "Could not create the project. Try again.",
      queue_failed: "Could not queue the job. Try again.",
      query_failed: "Request error.",
      not_found: "Project not found.",
      network: "Network unavailable. Try again.",
      invalid_email: "Enter a valid email address.",
      weak_password: "The password is too short — at least 6 characters.",
      email_taken: "This email is already registered — sign in instead.",
      signup_failed: "Could not create the account. Try again.",
      bad_credentials: "Wrong email or password.",
      unknown: "Something went wrong.",
    },
    auth: {
      title: "Sign in to Horsteppe",
      lead: "An account keeps your projects and protects the generation budget.",
      email: "Email",
      password: "Password",
      signIn: "Sign in",
      signUp: "Create account",
      toSignUp: "No account? Create one",
      toSignIn: "Already have an account? Sign in",
      confirm: "Check your inbox and confirm the address, then sign in.",
      working: "…",
    },
    library: {
      title: "My videos",
      active: "In production",
      done: "Ready",
      failed: "Failed",
      total: "Total",
      empty: "Nothing here yet.",
      emptyCta: "Create your first video",
      open: "Open",
      statuses: { queued: "Queued", generating: "Producing", done: "Ready", failed: "Failed" },
    },
    project: {
      back: "New video",
      queued: "Queued",
      working: "Producing your video",
      ready: "Video ready",
      failed: "Production failed",
      download: "Download MP4",
      again: "Create another",
      scenes: "Scenes",
      duration: "Duration",
      retry: "Try again",
      stages: [
        "Understanding the project",
        "Writing the script",
        "Recording the voice",
        "Creating the visuals",
        "Editing",
        "Rendering the final video",
      ],
    },
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
      "Сборка занимает несколько минут. Страницу можно закрыть и вернуться — проект продолжит собираться.",
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
    errors: {
      backend_not_configured: "Генерация ещё не подключена — администратор не настроил доступ к базе.",
      unauthorized: "Войдите, чтобы создать видео.",
      invalid_request: "Некорректный запрос.",
      topic_too_short: "Сначала напишите пару предложений о ролике.",
      topic_too_long: "Описание слишком длинное — уложитесь в 500 символов.",
      rate_limit_concurrent: "У вас уже собирается ролик. Его состояние видно на странице «Мои видео».",
      rate_limit_daily: "Суточный лимит исчерпан. Попробуйте завтра.",
      create_failed: "Не удалось создать проект. Попробуйте ещё раз.",
      queue_failed: "Не удалось поставить задачу в очередь. Попробуйте ещё раз.",
      query_failed: "Ошибка запроса.",
      not_found: "Проект не найден.",
      network: "Сеть недоступна. Попробуйте ещё раз.",
      invalid_email: "Введите корректный адрес почты.",
      weak_password: "Пароль слишком короткий — минимум 6 символов.",
      email_taken: "Эта почта уже зарегистрирована — войдите.",
      signup_failed: "Не удалось создать аккаунт. Попробуйте ещё раз.",
      bad_credentials: "Неверная почта или пароль.",
      unknown: "Что-то пошло не так.",
    },
    auth: {
      title: "Вход в Horsteppe",
      lead: "Аккаунт хранит ваши проекты и защищает бюджет генерации.",
      email: "Почта",
      password: "Пароль",
      signIn: "Войти",
      signUp: "Создать аккаунт",
      toSignUp: "Нет аккаунта? Создать",
      toSignIn: "Уже есть аккаунт? Войти",
      confirm: "Проверьте почту, подтвердите адрес и войдите.",
      working: "…",
    },
    library: {
      title: "Мои видео",
      active: "В работе",
      done: "Готово",
      failed: "Не вышло",
      total: "Всего",
      empty: "Пока пусто.",
      emptyCta: "Создать первый ролик",
      open: "Открыть",
      statuses: { queued: "В очереди", generating: "Собирается", done: "Готово", failed: "Ошибка" },
    },
    project: {
      back: "Новое видео",
      queued: "В очереди",
      working: "Собираем ваш ролик",
      ready: "Ролик готов",
      failed: "Не удалось собрать ролик",
      download: "Скачать MP4",
      again: "Создать ещё",
      scenes: "Сцены",
      duration: "Длительность",
      retry: "Попробовать снова",
      stages: [
        "Разбираем задачу",
        "Пишем сценарий",
        "Записываем голос",
        "Создаём визуал",
        "Монтируем",
        "Рендерим финальное видео",
      ],
    },
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
      "Жинау бірнеше минут алады. Бетті жабуға болады — жоба жиналуын жалғастырады.",
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
    errors: {
      backend_not_configured: "Генерация әлі қосылмаған — әкімші дерекқорға қолжетімділікті баптамаған.",
      unauthorized: "Бейне жасау үшін кіріңіз.",
      invalid_request: "Қате сұраныс.",
      topic_too_short: "Алдымен ролик туралы бірер сөйлем жазыңыз.",
      topic_too_long: "Сипаттама тым ұзын — 500 таңбаға сыйдырыңыз.",
      rate_limit_concurrent: "Сізде бейне жасалып жатыр. Оның күйі «Менің бейнелерім» бетінде көрінеді.",
      rate_limit_daily: "Тәуліктік шек таусылды. Ертең қайталаңыз.",
      create_failed: "Жобаны жасау мүмкін болмады. Қайталап көріңіз.",
      queue_failed: "Тапсырманы кезекке қою мүмкін болмады. Қайталап көріңіз.",
      query_failed: "Сұраныс қатесі.",
      not_found: "Жоба табылмады.",
      network: "Желі қолжетімсіз. Қайталап көріңіз.",
      invalid_email: "Жарамды пошта мекенжайын енгізіңіз.",
      weak_password: "Құпиясөз тым қысқа — кемінде 6 таңба.",
      email_taken: "Бұл пошта тіркелген — кіріңіз.",
      signup_failed: "Аккаунт жасау мүмкін болмады. Қайталап көріңіз.",
      bad_credentials: "Пошта немесе құпиясөз қате.",
      unknown: "Бірдеңе дұрыс болмады.",
    },
    auth: {
      title: "Horsteppe-ке кіру",
      lead: "Аккаунт жобаларыңызды сақтайды және генерация бюджетін қорғайды.",
      email: "Пошта",
      password: "Құпиясөз",
      signIn: "Кіру",
      signUp: "Аккаунт жасау",
      toSignUp: "Аккаунт жоқ па? Жасау",
      toSignIn: "Аккаунт бар ма? Кіру",
      confirm: "Поштаңызды тексеріп, мекенжайды растаңыз да, кіріңіз.",
      working: "…",
    },
    library: {
      title: "Менің бейнелерім",
      active: "Жұмыста",
      done: "Дайын",
      failed: "Шықпады",
      total: "Барлығы",
      empty: "Әзірге бос.",
      emptyCta: "Алғашқы роликті жасау",
      open: "Ашу",
      statuses: { queued: "Кезекте", generating: "Жиналуда", done: "Дайын", failed: "Қате" },
    },
    project: {
      back: "Жаңа бейне",
      queued: "Кезекте",
      working: "Ролигіңізді жинап жатырмыз",
      ready: "Ролик дайын",
      failed: "Роликті жинау мүмкін болмады",
      download: "MP4 жүктеу",
      again: "Тағы жасау",
      scenes: "Сценалар",
      duration: "Ұзақтығы",
      retry: "Қайталап көру",
      stages: [
        "Тапсырманы талдаймыз",
        "Сценарий жазамыз",
        "Дауыс жазамыз",
        "Кадр жасаймыз",
        "Монтаждаймыз",
        "Финалдық бейнені рендерлейміз",
      ],
    },
  },
};
