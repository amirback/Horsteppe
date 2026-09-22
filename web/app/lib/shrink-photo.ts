/**
 * Уменьшение фотографии в браузере — до отправки на сервер.
 *
 * Зачем. Снимок с телефона это 3–12 МБ и 4032 px по длинной стороне. Движок
 * всё равно вписывает его в квадрат 1536 px (worker/references.py), то есть
 * лишние пиксели выбрасываются — но сначала едут по мобильной сети целиком.
 *
 * И это не только медленно. У площадки, где живёт сайт, жёсткий предел на
 * тело запроса — 4.5 МБ. Две фотографии с телефона его превышают, и человек
 * получал отказ раньше, чем срабатывала наша собственная проверка размера:
 * вместо понятного текста — пустая ошибка загрузки.
 *
 * Поворот. Пересжатие стирает метаданные, в том числе ориентацию из EXIF.
 * Не применить её к пикселям — значит положить снимок набок, причём молча:
 * в галерее телефона он выглядел правильно.
 *
 * У браузера есть готовое средство — `imageOrientation: "from-image"`, — но
 * полагаться на него нельзя: неподдерживающий браузер проигнорирует параметр
 * НЕ подняв ошибки, и мы получим ровно то, чего избегаем. Поэтому поворот
 * разбирается из файла и применяется руками, а браузеру явно запрещено
 * делать это за нас: иначе снимок повернётся дважды.
 *
 * Любая неудача означает «отправляем оригинал»: движок умеет и EXIF, и
 * уменьшение. Уменьшение здесь — ускорение, а не обязательный шаг.
 */

/** Совпадает с MAX_SIDE в worker/references.py. Больше движку не нужно. */
export const MAX_SIDE = 1536;

/**
 * Ниже этого веса трогать файл незачем: пересжатие стоило бы резкости и не
 * дало бы ничего. Тот же принцип, что в движке, — лучший исход это «ничего
 * не делать».
 */
export const LEAVE_ALONE_BYTES = 1_200_000;

/** Качество JPEG при пересжатии. 0.9 — граница, за которой видна разница. */
const QUALITY = 0.9;

export type ShrinkResult = {
  file: File;
  shrunk: boolean;
};

/**
 * Ориентация из EXIF: 1 — нормальная, 8 — поворот на 270°. Ноль означает
 * «не нашлось», и это то же самое, что 1.
 *
 * Разбор ручной: ставить библиотеку ради одного числа контракт проекта
 * запрещает, а число это всего лишь тег 0x0112 в первой таблице TIFF.
 */
export function readExifOrientation(bytes: Uint8Array): number {
  if (bytes.length < 4 || bytes[0] !== 0xff || bytes[1] !== 0xd8) return 1; // не JPEG
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  let offset = 2;

  while (offset + 4 <= bytes.length) {
    if (bytes[offset] !== 0xff) return 1;
    const marker = bytes[offset + 1];
    if (marker === 0xda || marker === 0xd9) return 1; // пошли данные — EXIF не будет
    const size = view.getUint16(offset + 2);
    if (size < 2) return 1;

    if (marker === 0xe1 && offset + 10 <= bytes.length) {
      const isExif =
        bytes[offset + 4] === 0x45 && bytes[offset + 5] === 0x78 &&
        bytes[offset + 6] === 0x69 && bytes[offset + 7] === 0x66;
      if (isExif) return orientationFromTiff(view, offset + 10, offset + 2 + size);
    }
    offset += 2 + size;
  }
  return 1;
}

function orientationFromTiff(view: DataView, start: number, end: number): number {
  try {
    const little = view.getUint16(start) === 0x4949; // "II" против "MM"
    if (view.getUint16(start + 2, little) !== 0x002a) return 1;

    const ifd = start + view.getUint32(start + 4, little);
    const count = view.getUint16(ifd, little);
    for (let i = 0; i < count; i++) {
      const entry = ifd + 2 + i * 12;
      if (entry + 12 > end) break;
      if (view.getUint16(entry, little) === 0x0112) {
        const value = view.getUint16(entry + 8, little);
        return value >= 1 && value <= 8 ? value : 1;
      }
    }
  } catch {
    return 1;
  }
  return 1;
}

/** Меняет ли эта ориентация ширину с высотой местами. */
function swapsSides(orientation: number): boolean {
  return orientation >= 5 && orientation <= 8;
}

/** Преобразование холста, приводящее пиксели к нормальному виду. */
function applyOrientation(
  context: CanvasRenderingContext2D, orientation: number, w: number, h: number
): void {
  switch (orientation) {
    case 2: context.transform(-1, 0, 0, 1, w, 0); break;
    case 3: context.transform(-1, 0, 0, -1, w, h); break;
    case 4: context.transform(1, 0, 0, -1, 0, h); break;
    case 5: context.transform(0, 1, 1, 0, 0, 0); break;
    case 6: context.transform(0, 1, -1, 0, w, 0); break;
    case 7: context.transform(0, -1, -1, 0, w, h); break;
    case 8: context.transform(0, -1, 1, 0, 0, h); break;
    default: break;
  }
}

export async function shrinkPhoto(file: File): Promise<ShrinkResult> {
  if (typeof createImageBitmap !== "function" || typeof document === "undefined") {
    return { file, shrunk: false };
  }

  let orientation = 1;
  try {
    orientation = readExifOrientation(new Uint8Array(await file.arrayBuffer()));
  } catch {
    return { file, shrunk: false };
  }

  let bitmap: ImageBitmap;
  try {
    // "none" — обязательно. Иначе браузер, умеющий EXIF, повернёт кадр сам,
    // а мы повернём его второй раз.
    bitmap = await createImageBitmap(file, { imageOrientation: "none" });
  } catch {
    return { file, shrunk: false };
  }

  try {
    const longest = Math.max(bitmap.width, bitmap.height);
    if (file.size <= LEAVE_ALONE_BYTES && longest <= MAX_SIDE && orientation === 1) {
      return { file, shrunk: false };
    }

    const scale = Math.min(1, MAX_SIDE / longest);
    const drawW = Math.max(1, Math.round(bitmap.width * scale));
    const drawH = Math.max(1, Math.round(bitmap.height * scale));

    const canvas = document.createElement("canvas");
    canvas.width = swapsSides(orientation) ? drawH : drawW;
    canvas.height = swapsSides(orientation) ? drawW : drawH;

    const context = canvas.getContext("2d");
    if (!context) return { file, shrunk: false };
    applyOrientation(context, orientation, drawW, drawH);
    context.drawImage(bitmap, 0, 0, drawW, drawH);

    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, "image/jpeg", QUALITY)
    );
    if (!blob || blob.size === 0) return { file, shrunk: false };

    // Пересжатие, сделавшее файл тяжелее, — это не уменьшение. Так бывает на
    // скриншотах: ровные заливки PNG жмёт лучше JPEG. Но если снимок надо
    // было повернуть, оригинал возвращать нельзя — он ляжет набок.
    if (blob.size >= file.size && longest <= MAX_SIDE && orientation === 1) {
      return { file, shrunk: false };
    }

    const name = file.name.replace(/\.[^.]+$/, "") || "photo";
    return {
      file: new File([blob], `${name}.jpg`, { type: "image/jpeg" }),
      shrunk: true,
    };
  } catch {
    return { file, shrunk: false };
  } finally {
    bitmap.close();
  }
}
