import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { CreateForm } from "./create-form";

const EXAMPLE_STYLES = [
  {
    name: "Кинематографичный",
    tag: "cinematic",
    gradient: "from-orange-500/80 via-rose-600/70 to-slate-900",
  },
  {
    name: "Аниме",
    tag: "anime",
    gradient: "from-pink-400/80 via-fuchsia-600/70 to-indigo-900",
  },
  {
    name: "Киберпанк",
    tag: "cyberpunk",
    gradient: "from-cyan-400/80 via-purple-600/70 to-slate-950",
  },
  {
    name: "Документальный",
    tag: "documentary",
    gradient: "from-amber-300/70 via-stone-600/70 to-stone-950",
  },
  {
    name: "Акварель",
    tag: "watercolor",
    gradient: "from-sky-300/80 via-teal-500/60 to-blue-900",
  },
];

const FEATURES = [
  {
    icon: "✍️",
    title: "ИИ-сценарист",
    body: "Пишет историю по вашей теме: хук в первые секунды, развитие и финал. Разбивает на сцены сам.",
  },
  {
    icon: "🎙",
    title: "Живая озвучка",
    body: "Профессиональный ИИ-голос читает сценарий естественно, с интонациями — не «робот из навигатора».",
  },
  {
    icon: "🎨",
    title: "Кадры под каждую сцену",
    body: "Для каждой сцены генерируется свой визуал в выбранном стиле — от кино до аниме.",
  },
  {
    icon: "🎬",
    title: "Автомонтаж",
    body: "Кадры, озвучка и движение камеры склеиваются в готовый ролик. Ноль кликов в редакторе.",
  },
  {
    icon: "📱",
    title: "Вертикальный формат",
    body: "1080×1920 Full HD — родной формат Reels, TikTok и Shorts. Публикуйте сразу.",
  },
  {
    icon: "⚡️",
    title: "Минуты, не часы",
    body: "Обычный цикл «сценарий → съёмка → монтаж» занимает дни. Здесь — несколько минут.",
  },
];

const USE_CASES = [
  {
    title: "Reels / TikTok / Shorts",
    body: "Регулярный контент без съёмок: факты, истории, подборки, лайфхаки.",
  },
  {
    title: "Реклама и промо",
    body: "Быстрые видео-креативы для теста гипотез — дешевле, чем продакшн.",
  },
  {
    title: "Обучение",
    body: "Короткие объясняющие ролики по любой теме для курсов и уроков.",
  },
  {
    title: "Личный бренд",
    body: "Стабильный поток видео для блога, даже если нет времени на камеру.",
  },
];

const FAQ = [
  {
    q: "Сколько времени занимает генерация?",
    a: "Обычно несколько минут: ИИ пишет сценарий, озвучивает каждую сцену, генерирует кадры и монтирует их в один ролик. Страницу можно закрыть — готовое видео появится в «Моих видео».",
  },
  {
    q: "Почему длительность до 60 секунд?",
    a: "Видео собирается из сцен, и каждая сцена — это отдельная генерация озвучки и кадров. До 60 секунд ролик получается цельным, быстрым и качественным. Более длинные форматы — в разработке.",
  },
  {
    q: "Какой формат у готового видео?",
    a: "Вертикальный mp4 1080×1920 (9:16) — родной формат Reels, TikTok и YouTube Shorts. Скачиваете и публикуете без конвертации.",
  },
  {
    q: "Можно ли использовать видео в коммерческих целях?",
    a: "Да, готовые ролики можно публиковать и использовать в своих проектах. Учтите, что видео генерируются ИИ и могут содержать неточности — проверяйте факты в сценарии.",
  },
  {
    q: "На каком языке будет озвучка?",
    a: "Озвучка генерируется на языке вашей темы. Напишете тему на русском — получите русскую озвучку.",
  },
];

export default async function HomePage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  return (
    <div className="space-y-24 sm:space-y-32">
      {/* Hero */}
      <section className="glow relative pt-6 text-center sm:pt-16">
        <span className="pill mb-6">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
          Тема → готовый ролик за минуты
        </span>
        <h1 className="mx-auto max-w-3xl text-balance text-4xl font-semibold leading-[1.08] tracking-tight sm:text-6xl sm:leading-[1.05]">
          Видео, которое{" "}
          <span className="bg-gradient-to-r from-violet-400 via-fuchsia-400 to-orange-300 bg-clip-text text-transparent">
            снимает себя само
          </span>
        </h1>
        <p className="mx-auto mt-5 max-w-lg text-balance text-base leading-relaxed text-neutral-400 sm:mt-6 sm:text-lg">
          Введите тему — получите готовый вертикальный ролик: сценарий, кадры,
          озвучка и монтаж без единого клика в редакторе.
        </p>

        {!user && (
          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:mt-10 sm:flex-row">
            <Link href="/login" className="btn-primary w-full max-w-xs sm:w-auto">
              Начать бесплатно
            </Link>
            <a href="#examples" className="btn-secondary w-full max-w-xs sm:w-auto">
              Посмотреть примеры
            </a>
          </div>
        )}
        {!user && (
          <p className="mt-5 text-xs text-neutral-500">
            Без карты · Регистрация за минуту
          </p>
        )}
      </section>

      {/* Create form for logged-in users */}
      {user && (
        <section className="!mt-12">
          <CreateForm />
        </section>
      )}

      {/* Style examples */}
      <section id="examples" className="scroll-mt-24 space-y-10">
        <div className="text-center">
          <p className="label mb-3">Стили</p>
          <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">
            Один клик — любой визуальный стиль
          </h2>
          <p className="mx-auto mt-3 max-w-md text-sm leading-relaxed text-neutral-400">
            Выберите стиль при создании — каждая сцена ролика будет выдержана в нём.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 sm:gap-4 lg:grid-cols-5">
          {EXAMPLE_STYLES.map((s) => (
            <div
              key={s.tag}
              className={`group relative aspect-[9/16] overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-b ${s.gradient} transition-transform duration-300 hover:scale-[1.02]`}
            >
              <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(255,255,255,0.15),transparent_60%)]" />
              <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent p-4 pt-10">
                <p className="text-sm font-semibold text-white">{s.name}</p>
                <p className="mt-0.5 text-[11px] uppercase tracking-wider text-white/60">
                  {s.tag}
                </p>
              </div>
              <div className="absolute left-1/2 top-1/2 flex h-11 w-11 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-white/20 backdrop-blur-sm transition-transform group-hover:scale-110">
                <span className="ml-0.5 text-white">▶</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Stats */}
      <section className="grid grid-cols-2 gap-3 sm:grid-cols-4 sm:gap-4">
        {[
          ["~5 мин", "на один ролик"],
          ["1080×1920", "Full HD, 9:16"],
          ["5 стилей", "от кино до аниме"],
          ["0 кликов", "в видеоредакторе"],
        ].map(([big, small]) => (
          <div key={big} className="card p-5 text-center sm:p-7">
            <p className="text-2xl font-semibold tracking-tight sm:text-3xl">{big}</p>
            <p className="mt-1 text-xs text-neutral-500 sm:text-sm">{small}</p>
          </div>
        ))}
      </section>

      {/* How it works */}
      <section id="how" className="scroll-mt-24 space-y-10">
        <div className="text-center">
          <p className="label mb-3">Процесс</p>
          <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">
            Три шага, ноль монтажа
          </h2>
        </div>
        <div className="grid gap-4 sm:grid-cols-3 sm:gap-5">
          {[
            {
              n: "01",
              title: "Опишите тему",
              body: "Одно предложение: «5 фактов о космосе» или «история кофе». Выберите стиль и длительность.",
            },
            {
              n: "02",
              title: "ИИ делает всё",
              body: "Сценарий, озвучка каждой сцены, кадры в вашем стиле и движение камеры — автоматически.",
            },
            {
              n: "03",
              title: "Скачайте и публикуйте",
              body: "Готовый вертикальный mp4 в Full HD. Сразу в Reels, TikTok или Shorts.",
            },
          ].map((step) => (
            <div key={step.n} className="card p-6 transition-colors hover:bg-white/[0.05] sm:p-8">
              <span className="pill">{step.n}</span>
              <h3 className="mt-5 text-lg font-semibold">{step.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-neutral-400">{step.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section id="features" className="scroll-mt-24 space-y-10">
        <div className="text-center">
          <p className="label mb-3">Возможности</p>
          <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">
            Полный продакшн внутри
          </h2>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 sm:gap-5 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <div key={f.title} className="card p-6 transition-colors hover:bg-white/[0.05] sm:p-7">
              <span className="text-2xl">{f.icon}</span>
              <h3 className="mt-4 font-semibold">{f.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-neutral-400">{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Use cases */}
      <section className="space-y-10">
        <div className="text-center">
          <p className="label mb-3">Кому подходит</p>
          <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">
            Контент без съёмочной команды
          </h2>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 sm:gap-5 lg:grid-cols-4">
          {USE_CASES.map((u) => (
            <div key={u.title} className="card p-6">
              <h3 className="font-semibold">{u.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-neutral-400">{u.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="scroll-mt-24 space-y-10">
        <div className="text-center">
          <p className="label mb-3">Тарифы</p>
          <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">
            Начните бесплатно
          </h2>
        </div>
        <div className="mx-auto grid max-w-4xl gap-4 sm:grid-cols-3 sm:gap-5">
          <div className="card flex flex-col p-6 sm:p-8">
            <p className="font-semibold">Старт</p>
            <p className="mt-3 text-3xl font-semibold tracking-tight">
              $0
              <span className="text-sm font-normal text-neutral-500"> / мес</span>
            </p>
            <ul className="mt-6 flex-1 space-y-3 text-sm text-neutral-400">
              <li>✓ Видео до 60 секунд</li>
              <li>✓ Все 5 стилей</li>
              <li>✓ Full HD 1080×1920</li>
              <li>✓ ИИ-озвучка</li>
            </ul>
            <Link href={user ? "/" : "/login"} className="btn-secondary mt-8 w-full">
              {user ? "Создать видео" : "Начать"}
            </Link>
          </div>
          <div className="relative flex flex-col rounded-2xl border border-violet-400/40 bg-gradient-to-b from-violet-500/10 to-transparent p-6 sm:p-8">
            <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-gradient-to-r from-violet-500 to-fuchsia-500 px-3 py-1 text-[11px] font-semibold text-white">
              Скоро
            </span>
            <p className="font-semibold">Pro</p>
            <p className="mt-3 text-3xl font-semibold tracking-tight">
              $19
              <span className="text-sm font-normal text-neutral-500"> / мес</span>
            </p>
            <ul className="mt-6 flex-1 space-y-3 text-sm text-neutral-400">
              <li>✓ Всё из «Старт»</li>
              <li>✓ Видео до 3 минут</li>
              <li>✓ ИИ-анимация кадров</li>
              <li>✓ Выбор голоса</li>
              <li>✓ Приоритетная очередь</li>
            </ul>
            <button disabled className="btn-primary mt-8 w-full">
              Скоро
            </button>
          </div>
          <div className="card flex flex-col p-6 sm:p-8">
            <p className="font-semibold">Business</p>
            <p className="mt-3 text-3xl font-semibold tracking-tight">
              $49
              <span className="text-sm font-normal text-neutral-500"> / мес</span>
            </p>
            <ul className="mt-6 flex-1 space-y-3 text-sm text-neutral-400">
              <li>✓ Всё из Pro</li>
              <li>✓ Командный доступ</li>
              <li>✓ Свой брендинг</li>
              <li>✓ API-доступ</li>
            </ul>
            <button disabled className="btn-secondary mt-8 w-full">
              Скоро
            </button>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section id="faq" className="scroll-mt-24 space-y-10">
        <div className="text-center">
          <p className="label mb-3">FAQ</p>
          <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">
            Частые вопросы
          </h2>
        </div>
        <div className="mx-auto max-w-2xl space-y-3">
          {FAQ.map((item) => (
            <details key={item.q} className="card group px-6 py-4 open:bg-white/[0.05]">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-sm font-medium [&::-webkit-details-marker]:hidden">
                {item.q}
                <span className="shrink-0 text-neutral-500 transition-transform group-open:rotate-45">
                  +
                </span>
              </summary>
              <p className="mt-3 text-sm leading-relaxed text-neutral-400">{item.a}</p>
            </details>
          ))}
        </div>
      </section>

      {/* Final CTA */}
      {!user && (
        <section className="relative overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-b from-violet-500/15 via-fuchsia-500/5 to-transparent px-6 py-14 text-center sm:px-8 sm:py-20">
          <h2 className="text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
            Первое видео — уже через пару минут
          </h2>
          <p className="mx-auto mt-4 max-w-md text-sm leading-relaxed text-neutral-400">
            Регистрация занимает меньше минуты. Карта не нужна.
          </p>
          <Link href="/login" className="btn-primary mt-8">
            Создать аккаунт
          </Link>
        </section>
      )}
    </div>
  );
}
