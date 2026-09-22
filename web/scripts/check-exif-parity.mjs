/**
 * Сверка разбора EXIF: браузер против движка.
 *
 * Зачем. Сайт уменьшает фотографию до отправки, и пересжатие стирает EXIF —
 * в том числе ориентацию. Не применить её к пикселям значит положить снимок
 * набок, причём молча: в галерее телефона он выглядел правильно.
 *
 * Чтобы этого не случилось, ориентация разбирается на клиенте своими руками
 * (`app/lib/shrink-photo.ts`). Два разбора одного и того же — это два места,
 * где можно разойтись. Этот скрипт кормит обоим одни и те же байты и требует
 * одинакового ответа.
 *
 * Тестового движка на сайте нет, а ставить его контракт проекта запрещает,
 * поэтому проверка сделана скриптом на голом Node.
 *
 * Запуск из каталога web:
 *     node scripts/check-exif-parity.mjs
 */
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { execFileSync } from "node:child_process";

const WEB = path.resolve(import.meta.dirname, "..");
const ROOT = path.resolve(WEB, "..");
const WORKER = path.join(ROOT, "worker");
const PYTHON = path.join(WORKER, ".venv", "bin", "python");

const ORIENTATIONS = [1, 2, 3, 4, 5, 6, 7, 8];

/** Минимальный JPEG с одним тегом Orientation. Порядок байтов — оба. */
function jpegWithOrientation(orientation, little) {
  const tiff = Buffer.alloc(14);
  if (little) {
    tiff.write("II", 0);
    tiff.writeUInt16LE(42, 2);
    tiff.writeUInt32LE(8, 4);
    tiff.writeUInt16LE(1, 8);
  } else {
    tiff.write("MM", 0);
    tiff.writeUInt16BE(42, 2);
    tiff.writeUInt32BE(8, 4);
    tiff.writeUInt16BE(1, 8);
  }
  const entry = Buffer.alloc(12);
  const next = Buffer.alloc(4);
  if (little) {
    entry.writeUInt16LE(0x0112, 0);
    entry.writeUInt16LE(3, 2);
    entry.writeUInt32LE(1, 4);
    entry.writeUInt16LE(orientation, 8);
  } else {
    entry.writeUInt16BE(0x0112, 0);
    entry.writeUInt16BE(3, 2);
    entry.writeUInt32BE(1, 4);
    entry.writeUInt16BE(orientation, 8);
  }
  const payload = Buffer.concat([Buffer.from("Exif\0\0", "binary"), tiff.subarray(0, 10), entry, next]);
  const app1 = Buffer.concat([
    Buffer.from([0xff, 0xe1]),
    (() => { const b = Buffer.alloc(2); b.writeUInt16BE(payload.length + 2); return b; })(),
    payload,
  ]);
  return Buffer.concat([
    Buffer.from([0xff, 0xd8]), app1,
    Buffer.from([0xff, 0xdb, 0x00, 0x04, 0x00, 0x00]),
    Buffer.from([0xff, 0xd9]),
  ]);
}

/** Вырезать из модуля чистую часть: остальное требует браузера. */
async function loadBrowserParser() {
  const source = fs.readFileSync(path.join(WEB, "app/lib/shrink-photo.ts"), "utf8");
  const from = source.indexOf("export function readExifOrientation");
  const to = source.indexOf("/** Меняет ли эта ориентация");
  if (from < 0 || to < 0) throw new Error("не нашёл readExifOrientation в shrink-photo.ts");
  const code = source.slice(from, to)
    .replace(/export /g, "")
    .replace(/: Uint8Array|: DataView|: number|: boolean/g, "")
    + "\nexport { readExifOrientation };\n";
  const temp = path.join(os.tmpdir(), `exif-parity-${process.pid}.mjs`);
  fs.writeFileSync(temp, code);
  try {
    return (await import(`file://${temp}`)).readExifOrientation;
  } finally {
    fs.rmSync(temp, { force: true });
  }
}

function engineAnswers(files) {
  const script = `
import json, sys
sys.path.insert(0, ${JSON.stringify(WORKER)})
import references
paths = json.loads(sys.stdin.read())
print(json.dumps({n: references.read_exif_orientation(open(p, "rb").read()) for n, p in paths.items()}))
`;
  const out = execFileSync(PYTHON, ["-c", script], { input: JSON.stringify(files), encoding: "utf8" });
  return JSON.parse(out);
}

const dir = fs.mkdtempSync(path.join(os.tmpdir(), "exif-parity-"));
const files = {};
for (const o of ORIENTATIONS) {
  for (const [tag, little] of [["le", true], ["be", false]]) {
    const name = `o${o}_${tag}.jpg`;
    const file = path.join(dir, name);
    fs.writeFileSync(file, jpegWithOrientation(o, little));
    files[name] = file;
  }
}
for (const [name, bytes] of Object.entries({
  "no_exif.jpg": Buffer.from([0xff, 0xd8, 0xff, 0xd9]),
  "png.png": Buffer.concat([Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]), Buffer.alloc(32)]),
  "truncated.jpg": Buffer.from([0xff, 0xd8, 0xff, 0xe1, 0x00, 0x08, 0x61, 0x62, 0x63, 0x64]),
  "empty.bin": Buffer.alloc(0),
})) {
  const file = path.join(dir, name);
  fs.writeFileSync(file, bytes);
  files[name] = file;
}

const browser = await loadBrowserParser();
const engine = engineAnswers(files);

let mismatched = 0;
for (const [name, file] of Object.entries(files)) {
  const got = browser(new Uint8Array(fs.readFileSync(file)));
  const want = engine[name];
  const ok = got === want;
  if (!ok) mismatched++;
  console.log(`${ok ? "✓" : "✗"} ${name.padEnd(16)} движок ${want}  браузер ${got}`);
}
fs.rmSync(dir, { recursive: true, force: true });

console.log(mismatched === 0
  ? `\nСОВПАДАЕТ ПОЛНОСТЬЮ (${Object.keys(files).length} случаев)`
  : `\nРАСХОЖДЕНИЙ: ${mismatched}`);
process.exit(mismatched === 0 ? 0 : 1);
