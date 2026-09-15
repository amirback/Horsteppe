import type { Lang } from "./i18n";
import type { Option } from "./studio-content";

/**
 * Тексты двух новых режимов: реклама товара и оживление фотографии.
 *
 * Отдельным файлом, а не внутри studio-content: там три параллельных языковых
 * блока по полтораста строк, и правка вслепую в середине такого файла —
 * лучший способ разъехаться переводами.
 *
 * Казахский переведён машинно и требует вычитки носителем — как и остальной
 * казахский на сайте.
 */
export type ProductDict = {
  modes: { video: string; ad: string; animate: string };
  photos: {
    label: string;
    hint: string;
    add: string;
    remove: string;
    primary: string;
  };
  fields: {
    name: string;
    namePlaceholder: string;
    description: string;
    descriptionPlaceholder: string;
    benefits: string;
    benefitsPlaceholder: string;
    audience: string;
    audiencePlaceholder: string;
    cta: string;
    ctaPlaceholder: string;
    goal: string;
    goalOptions: Option[];
    budget: string;
    budgetHint: string;
  };
  animate: { motion: string; motionPlaceholder: string };
  submitAd: string;
  submitAnimate: string;
  uploading: string;
  errors: Record<string, string>;
};

export const productStudio: Record<Lang, ProductDict> = {
  en: {
    modes: { video: "Video from a prompt", ad: "Product ad", animate: "Animate a photo" },
    photos: {
      label: "Product photos",
      hint: "1–5 photos, JPG / PNG / WebP, up to 8 MB each. The first one is the main view.",
      add: "Add photos",
      remove: "Remove",
      primary: "Main",
    },
    fields: {
      name: "Product name",
      namePlaceholder: "Reusable steel bottle",
      description: "What it is",
      descriptionPlaceholder: "700 ml, keeps drinks cold for 12 hours",
      benefits: "Main benefits",
      benefitsPlaceholder: "Doesn't leak; light enough for a backpack",
      audience: "Audience",
      audiencePlaceholder: "Students",
      cta: "Call to action",
      ctaPlaceholder: "Order on the website",
      goal: "Goal",
      goalOptions: [
        { value: "sales", label: "Sales" },
        { value: "launch", label: "Launch" },
        { value: "awareness", label: "Awareness" },
        { value: "other", label: "Other" },
      ],
      budget: "Generation budget, $",
      budgetHint: "Leave empty for no limit. Real video costs about $0.35 per five seconds.",
    },
    animate: {
      motion: "Describe the motion",
      motionPlaceholder: "The camera moves closer while the subject turns toward the window",
    },
    submitAd: "Create the ad",
    submitAnimate: "Create the video",
    uploading: "Uploading photos…",
    errors: {
      no_files: "Add at least one photo.",
      too_many_files: "Five photos is the maximum.",
      file_too_large: "That file is over 8 MB.",
      unsupported_format: "Only JPG, PNG and WebP are supported.",
      corrupted_image: "That file could not be read as an image.",
      image_too_small: "The photo is too small — at least 256 px on the shorter side.",
      empty_file: "That file is empty.",
      upload_failed: "The photo could not be uploaded. Try again.",
      invalid_references: "Something is wrong with the uploaded photos. Add them again.",
      reference_move_failed: "The photos could not be attached to the project.",
      reference_save_failed: "The photos could not be attached to the project.",
      product_name_required: "Enter the product name.",
      photo_required: "Add a photo to animate.",
      invalid_budget: "The budget must be a number between 0 and 20.",
    },
  },
  ru: {
    modes: { video: "Ролик по описанию", ad: "Реклама товара", animate: "Оживить фото" },
    photos: {
      label: "Фотографии товара",
      hint: "1–5 фотографий, JPG / PNG / WebP, до 8 МБ каждая. Первая — главный вид.",
      add: "Добавить фото",
      remove: "Убрать",
      primary: "Главная",
    },
    fields: {
      name: "Название товара",
      namePlaceholder: "Многоразовая стальная бутылка",
      description: "Что это",
      descriptionPlaceholder: "700 мл, держит холод 12 часов",
      benefits: "Главные выгоды",
      benefitsPlaceholder: "Не течёт; лёгкая, помещается в рюкзак",
      audience: "Аудитория",
      audiencePlaceholder: "Студенты",
      cta: "Призыв к действию",
      ctaPlaceholder: "Закажи на сайте",
      goal: "Цель",
      goalOptions: [
        { value: "sales", label: "Продажи" },
        { value: "launch", label: "Запуск" },
        { value: "awareness", label: "Узнаваемость" },
        { value: "other", label: "Другое" },
      ],
      budget: "Бюджет генерации, $",
      budgetHint: "Пусто — без потолка. Настоящее видео стоит около $0.35 за пять секунд.",
    },
    animate: {
      motion: "Опишите движение",
      motionPlaceholder: "Камера приближается, человек поворачивается к окну",
    },
    submitAd: "Собрать рекламу",
    submitAnimate: "Собрать видео",
    uploading: "Загружаем фотографии…",
    errors: {
      no_files: "Добавьте хотя бы одну фотографию.",
      too_many_files: "Больше пяти фотографий не нужно.",
      file_too_large: "Файл больше 8 МБ.",
      unsupported_format: "Подходят только JPG, PNG и WebP.",
      corrupted_image: "Файл не читается как картинка.",
      image_too_small: "Фотография слишком мелкая — нужно от 256 пикселей по короткой стороне.",
      empty_file: "Файл пустой.",
      upload_failed: "Не удалось загрузить фотографию. Попробуйте ещё раз.",
      invalid_references: "С загруженными фотографиями что-то не так. Добавьте их заново.",
      reference_move_failed: "Не удалось прикрепить фотографии к проекту.",
      reference_save_failed: "Не удалось прикрепить фотографии к проекту.",
      product_name_required: "Укажите название товара.",
      photo_required: "Добавьте фотографию, которую нужно оживить.",
      invalid_budget: "Бюджет — число от 0 до 20.",
    },
  },
  kk: {
    modes: { video: "Сипаттама бойынша ролик", ad: "Тауар жарнамасы", animate: "Фотоны жандандыру" },
    photos: {
      label: "Тауар фотосуреттері",
      hint: "1–5 фото, JPG / PNG / WebP, әрқайсысы 8 МБ дейін. Біріншісі — негізгі көрініс.",
      add: "Фото қосу",
      remove: "Алып тастау",
      primary: "Негізгі",
    },
    fields: {
      name: "Тауар атауы",
      namePlaceholder: "Көп реттік болат бөтелке",
      description: "Бұл не",
      descriptionPlaceholder: "700 мл, 12 сағат суықты сақтайды",
      benefits: "Басты артықшылықтары",
      benefitsPlaceholder: "Ақпайды; жеңіл, рюкзакқа сыяды",
      audience: "Аудитория",
      audiencePlaceholder: "Студенттер",
      cta: "Әрекетке шақыру",
      ctaPlaceholder: "Сайттан тапсырыс бер",
      goal: "Мақсат",
      goalOptions: [
        { value: "sales", label: "Сатылым" },
        { value: "launch", label: "Іске қосу" },
        { value: "awareness", label: "Танымалдық" },
        { value: "other", label: "Басқа" },
      ],
      budget: "Генерация бюджеті, $",
      budgetHint: "Бос — шектеусіз. Нақты видео бес секундына шамамен $0.35 тұрады.",
    },
    animate: {
      motion: "Қозғалысты сипаттаңыз",
      motionPlaceholder: "Камера жақындайды, адам терезеге қарай бұрылады",
    },
    submitAd: "Жарнама жинау",
    submitAnimate: "Видео жинау",
    uploading: "Фотосуреттер жүктелуде…",
    errors: {
      no_files: "Кемінде бір фото қосыңыз.",
      too_many_files: "Бес фотодан артық қажет емес.",
      file_too_large: "Файл 8 МБ-тан үлкен.",
      unsupported_format: "Тек JPG, PNG және WebP жарайды.",
      corrupted_image: "Файл сурет ретінде оқылмайды.",
      image_too_small: "Фото тым кішкентай — қысқа жағы кемінде 256 пиксель болуы керек.",
      empty_file: "Файл бос.",
      upload_failed: "Фотоны жүктеу мүмкін болмады. Қайталап көріңіз.",
      invalid_references: "Жүктелген фотолармен бірдеңе дұрыс емес. Қайта қосыңыз.",
      reference_move_failed: "Фотоларды жобаға тіркеу мүмкін болмады.",
      reference_save_failed: "Фотоларды жобаға тіркеу мүмкін болмады.",
      product_name_required: "Тауар атауын көрсетіңіз.",
      photo_required: "Жандандыратын фотоны қосыңыз.",
      invalid_budget: "Бюджет — 0-ден 20-ға дейінгі сан.",
    },
  },
};
