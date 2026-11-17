import type { Lang } from "./i18n";

/**
 * Тексты кабинета, пакетов и кредитов. Казахский — машинный перевод со
 * сверкой смысла; нужна вычитка носителем (docs/STATUS.md).
 */
export type Tier = "economy" | "medium" | "premium";
type Kind = "purchase" | "reserve" | "spend" | "release";
type OrderStatus = "pending" | "paid" | "canceled";

export type AccountDict = {
  title: string;
  balanceTitle: string;
  balanceEmpty: string;
  upTo: (sec: number) => string;
  available: string;
  inWork: string;
  tiers: Record<Tier, string>;
  tierHints: Record<Tier, string>;
  packagesTitle: string;
  packagesEmpty: string;
  packageLine: (videos: number, sec: number) => string;
  perVideo: (price: string) => string;
  buy: string;
  buying: string;
  ordersTitle: string;
  orderNo: string;
  orderStatus: Record<OrderStatus, string>;
  payTitle: string;
  payByDetails: (amount: string, order: string) => string;
  payByMail: (amount: string, order: string, email: string) => string;
  payAfter: string;
  historyTitle: string;
  historyEmpty: string;
  kinds: Record<Kind, string>;
  disabled: string;
  adminLink: string;
  credit: string;
  creditOption: (tier: string, left: number) => string;
  noCredits: string;
  buyPackage: string;
  errors: Record<string, string>;
};

const ru: AccountDict = {
  title: "Кабинет",
  balanceTitle: "Ваши кредиты",
  balanceEmpty: "Кредитов пока нет. Один кредит — один готовый ролик. Выберите пакет ниже.",
  upTo: (sec) => `до ${sec} с`,
  available: "доступно",
  inWork: "в работе",
  tiers: { economy: "Эконом", medium: "Медиум", premium: "Премиум" },
  tierHints: {
    economy: "лёгкие модели на всех кадрах",
    medium: "Kling 3.0 Pro и Seedance 2.0 на важных кадрах",
    premium: "Kling 4.0 и Seedance 2.5 на сложных кадрах",
  },
  packagesTitle: "Пакеты",
  packagesEmpty: "Пакеты скоро появятся.",
  packageLine: (videos, sec) => `${videos} роликов по ${sec} с`,
  perVideo: (price) => `${price} за ролик`,
  buy: "Купить",
  buying: "Оформляем…",
  ordersTitle: "Заказы",
  orderNo: "Заказ",
  orderStatus: { pending: "Ждёт оплаты", paid: "Оплачен", canceled: "Отменён" },
  payTitle: "Как оплатить",
  payByDetails: (amount, order) => `Переведите ${amount} по реквизитам ниже и укажите номер заказа ${order}.`,
  payByMail: (amount, order, email) =>
    `Напишите на ${email} номер заказа ${order} — пришлём счёт на ${amount}.`,
  payAfter: "Кредиты появятся сразу после подтверждения оплаты. Списывается кредит только за готовый ролик: при ошибке он вернётся сам.",
  historyTitle: "История",
  historyEmpty: "Движений пока не было.",
  kinds: { purchase: "Покупка пакета", reserve: "Взят под ролик", spend: "Ролик готов — списан", release: "Возвращён" },
  disabled: "Оплата пакетов ещё не подключена.",
  adminLink: "Касса",
  credit: "Пакет",
  creditOption: (tier, left) => `${tier} · осталось ${left}`,
  noCredits: "Нет кредитов на ролик.",
  buyPackage: "Купить пакет",
  errors: {
    no_credits: "Нет кредита нужного уровня и длины. Купите пакет в кабинете.",
    tier_required: "Выберите пакет, с которого списать ролик.",
    credits_error: "Не удалось взять кредит. Попробуйте ещё раз.",
    package_not_found: "Этот пакет больше не продаётся.",
    too_many_pending_orders: "У вас уже есть неоплаченные заказы — оплатите или дождитесь их отмены.",
    credits_disabled: "Оплата пакетов ещё не подключена.",
  },
};

const kk: AccountDict = {
  title: "Жеке кабинет",
  balanceTitle: "Сіздің кредиттеріңіз",
  balanceEmpty: "Әзірге кредит жоқ. Бір кредит — бір дайын ролик. Төменнен пакет таңдаңыз.",
  upTo: (sec) => `${sec} с дейін`,
  available: "қолжетімді",
  inWork: "жұмыста",
  tiers: { economy: "Эконом", medium: "Медиум", premium: "Премиум" },
  tierHints: {
    economy: "барлық кадрда жеңіл модельдер",
    medium: "маңызды кадрларда Kling 3.0 Pro және Seedance 2.0",
    premium: "күрделі кадрларда Kling 4.0 және Seedance 2.5",
  },
  packagesTitle: "Пакеттер",
  packagesEmpty: "Пакеттер жақында пайда болады.",
  packageLine: (videos, sec) => `${sec} секундтық ${videos} ролик`,
  perVideo: (price) => `бір ролик — ${price}`,
  buy: "Сатып алу",
  buying: "Ресімдеуде…",
  ordersTitle: "Тапсырыстар",
  orderNo: "Тапсырыс",
  orderStatus: { pending: "Төлемді күтуде", paid: "Төленді", canceled: "Бас тартылды" },
  payTitle: "Қалай төлеу керек",
  payByDetails: (amount, order) => `${amount} соманы төмендегі деректемелер бойынша аударып, ${order} тапсырыс нөмірін көрсетіңіз.`,
  payByMail: (amount, order, email) =>
    `${email} мекенжайына ${order} тапсырыс нөмірін жазыңыз — ${amount} сомаға шот жібереміз.`,
  payAfter: "Төлем расталған соң кредиттер бірден түседі. Кредит тек дайын ролик үшін алынады: қате болса, өзі қайтады.",
  historyTitle: "Тарих",
  historyEmpty: "Әзірге қозғалыс болған жоқ.",
  kinds: { purchase: "Пакет сатып алу", reserve: "Ролик үшін алынды", spend: "Ролик дайын — есептен шығарылды", release: "Қайтарылды" },
  disabled: "Пакеттерді төлеу әлі қосылмаған.",
  adminLink: "Касса",
  credit: "Пакет",
  creditOption: (tier, left) => `${tier} · ${left} қалды`,
  noCredits: "Ролик үшін кредит жоқ.",
  buyPackage: "Пакет сатып алу",
  errors: {
    no_credits: "Қажетті деңгей мен ұзақтықтағы кредит жоқ. Кабинетте пакет сатып алыңыз.",
    tier_required: "Ролик қай пакеттен есептен шығарылатынын таңдаңыз.",
    credits_error: "Кредит алу мүмкін болмады. Қайта көріңіз.",
    package_not_found: "Бұл пакет енді сатылмайды.",
    too_many_pending_orders: "Сізде төленбеген тапсырыстар бар — оларды төлеңіз немесе бас тартылуын күтіңіз.",
    credits_disabled: "Пакеттерді төлеу әлі қосылмаған.",
  },
};

const en: AccountDict = {
  title: "Account",
  balanceTitle: "Your credits",
  balanceEmpty: "No credits yet. One credit is one finished video. Pick a package below.",
  upTo: (sec) => `up to ${sec} s`,
  available: "available",
  inWork: "in progress",
  tiers: { economy: "Economy", medium: "Medium", premium: "Premium" },
  tierHints: {
    economy: "light models on every shot",
    medium: "Kling 3.0 Pro and Seedance 2.0 on key shots",
    premium: "Kling 4.0 and Seedance 2.5 on complex shots",
  },
  packagesTitle: "Packages",
  packagesEmpty: "Packages are coming soon.",
  packageLine: (videos, sec) => `${videos} videos × ${sec} s`,
  perVideo: (price) => `${price} per video`,
  buy: "Buy",
  buying: "Placing order…",
  ordersTitle: "Orders",
  orderNo: "Order",
  orderStatus: { pending: "Awaiting payment", paid: "Paid", canceled: "Canceled" },
  payTitle: "How to pay",
  payByDetails: (amount, order) => `Transfer ${amount} using the details below and quote order ${order}.`,
  payByMail: (amount, order, email) => `Email ${email} with order ${order} and we will send an invoice for ${amount}.`,
  payAfter: "Credits appear as soon as the payment is confirmed. A credit is only spent on a finished video; if generation fails, it comes back.",
  historyTitle: "History",
  historyEmpty: "No movements yet.",
  kinds: { purchase: "Package bought", reserve: "Held for a video", spend: "Video finished — spent", release: "Returned" },
  disabled: "Package payments are not switched on yet.",
  adminLink: "Till",
  credit: "Package",
  creditOption: (tier, left) => `${tier} · ${left} left`,
  noCredits: "No credits for a video.",
  buyPackage: "Buy a package",
  errors: {
    no_credits: "No credit of this level and length. Buy a package in your account.",
    tier_required: "Choose the package to spend this video from.",
    credits_error: "Could not hold a credit. Please try again.",
    package_not_found: "This package is no longer sold.",
    too_many_pending_orders: "You already have unpaid orders — pay them or wait until they are canceled.",
    credits_disabled: "Package payments are not switched on yet.",
  },
};

export const account: Record<Lang, AccountDict> = { ru, kk, en };

/** Сумма в тенге с пробелами по разрядам: 32 600 ₸. */
export function tenge(amount: number): string {
  return `${Math.round(amount).toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ")} ₸`;
}

/** Короткий номер заказа для перевода и переписки. */
export function orderCode(id: string): string {
  return id.slice(0, 8).toUpperCase();
}
