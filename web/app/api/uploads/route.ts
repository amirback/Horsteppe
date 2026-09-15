import { NextResponse } from "next/server";
import { randomUUID } from "node:crypto";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { isAdminReady } from "@/lib/supabase/env";

// Буферы и разбор заголовков картинок — это Node, не Edge.
export const runtime = "nodejs";

const BUCKET = "media";
// Не экспортируются: Next разрешает в файле маршрута только свой набор
// экспортов и падает на сборке от любого лишнего.
const MAX_FILES = 5;
const MAX_BYTES = 8 * 1024 * 1024;
// Меньше этого снимок бесполезен: провайдер вернёт мыло, и никакая настройка
// генерации этого не исправит. Порог совпадает с worker/references.py.
const MIN_SIDE = 256;

const TYPES: Record<string, string> = {
  "image/jpeg": "jpg",
  "image/png": "png",
  "image/webp": "webp",
};

/**
 * Формат определяется по содержимому файла, а не по расширению и не по
 * заголовку от браузера: и то и другое пишет клиент, а клиенту верить нельзя.
 */
function sniff(bytes: Uint8Array): string | null {
  if (bytes.length > 3 && bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) {
    return "image/jpeg";
  }
  if (
    bytes.length > 8 &&
    bytes[0] === 0x89 && bytes[1] === 0x50 && bytes[2] === 0x4e && bytes[3] === 0x47
  ) {
    return "image/png";
  }
  const ascii = (at: number, text: string) =>
    text.split("").every((ch, i) => bytes[at + i] === ch.charCodeAt(0));
  if (bytes.length > 12 && ascii(0, "RIFF") && ascii(8, "WEBP")) return "image/webp";
  return null;
}

/**
 * Размер картинки из заголовка. Своими руками, потому что ставить новую
 * зависимость ради трёх форматов запрещено контрактом проекта.
 */
function imageSize(bytes: Uint8Array, mime: string): { width: number; height: number } | null {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  try {
    if (mime === "image/png") {
      return { width: view.getUint32(16), height: view.getUint32(20) };
    }
    if (mime === "image/jpeg") {
      let offset = 2;
      while (offset + 9 < bytes.length) {
        if (bytes[offset] !== 0xff) return null;
        const marker = bytes[offset + 1];
        const size = view.getUint16(offset + 2);
        // SOF0…SOF15, кроме маркеров без размеров кадра.
        const isFrame = marker >= 0xc0 && marker <= 0xcf &&
          marker !== 0xc4 && marker !== 0xc8 && marker !== 0xcc;
        if (isFrame) {
          return { height: view.getUint16(offset + 5), width: view.getUint16(offset + 7) };
        }
        offset += 2 + size;
      }
      return null;
    }
    if (mime === "image/webp") {
      const format = String.fromCharCode(bytes[12], bytes[13], bytes[14], bytes[15]);
      if (format === "VP8X") {
        const w = 1 + (bytes[24] | (bytes[25] << 8) | (bytes[26] << 16));
        const h = 1 + (bytes[27] | (bytes[28] << 8) | (bytes[29] << 16));
        return { width: w, height: h };
      }
      if (format === "VP8 ") {
        return {
          width: view.getUint16(26, true) & 0x3fff,
          height: view.getUint16(28, true) & 0x3fff,
        };
      }
      if (format === "VP8L") {
        const bits = bytes[21] | (bytes[22] << 8) | (bytes[23] << 16) | (bytes[24] << 24);
        return { width: (bits & 0x3fff) + 1, height: ((bits >> 14) & 0x3fff) + 1 };
      }
    }
  } catch {
    return null;
  }
  return null;
}

/**
 * Приём фотографий пользователя.
 *
 * Файлы кладутся в личный отстойник и получают настоящие ссылки только при
 * создании проекта: иначе брошенная форма оставляла бы в хранилище мусор,
 * привязанный к несуществующему проекту.
 *
 * Ошибки — машинными кодами: сайт трёхъязычный, перевод живёт на клиенте.
 */
export async function POST(request: Request) {
  if (!isAdminReady()) {
    return NextResponse.json({ error: "backend_not_configured" }, { status: 503 });
  }

  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  let form: FormData;
  try {
    form = await request.formData();
  } catch {
    return NextResponse.json({ error: "invalid_request" }, { status: 400 });
  }

  const files = form.getAll("files").filter((f): f is File => f instanceof File);
  if (files.length === 0) {
    return NextResponse.json({ error: "no_files" }, { status: 400 });
  }
  if (files.length > MAX_FILES) {
    return NextResponse.json({ error: "too_many_files", limit: MAX_FILES }, { status: 400 });
  }

  const admin = createAdminClient();
  const batch = randomUUID();
  const items = [];

  for (const [index, file] of files.entries()) {
    if (file.size === 0) {
      return NextResponse.json({ error: "empty_file" }, { status: 400 });
    }
    if (file.size > MAX_BYTES) {
      return NextResponse.json(
        { error: "file_too_large", limit_mb: MAX_BYTES / 1024 / 1024 },
        { status: 400 }
      );
    }

    const bytes = new Uint8Array(await file.arrayBuffer());
    const mime = sniff(bytes);
    if (!mime || !TYPES[mime]) {
      return NextResponse.json({ error: "unsupported_format" }, { status: 400 });
    }

    const size = imageSize(bytes, mime);
    if (!size || !size.width || !size.height) {
      return NextResponse.json({ error: "corrupted_image" }, { status: 400 });
    }
    if (Math.min(size.width, size.height) < MIN_SIDE) {
      return NextResponse.json(
        { error: "image_too_small", min_side: MIN_SIDE },
        { status: 400 }
      );
    }

    // Имя файла придумывает сервер. Имя от пользователя может содержать что
    // угодно, включая переход по каталогам.
    const path = `staging/${user.id}/${batch}/${index}.${TYPES[mime]}`;
    const { error } = await admin.storage
      .from(BUCKET)
      .upload(path, bytes, { contentType: mime, upsert: true });
    if (error) {
      console.error("reference upload failed:", error.message);
      return NextResponse.json({ error: "upload_failed" }, { status: 500 });
    }

    items.push({
      path,
      mime_type: mime,
      width: size.width,
      height: size.height,
      bytes: file.size,
    });
  }

  return NextResponse.json({ items }, { status: 201 });
}
