/**
 * Сверка перевода строк сборщика.
 *
 * Сборщик пишет в базу ход работы и причины отказа по-русски, сайт
 * переводит их по точному списку (app/lib/worker-text.ts). Две копии
 * одних и тех же строк расходятся молча: стоит сборщику сказать
 * «Пишем сценарий…» чуть иначе — и английская страница покажет общий
 * текст вместо конкретного этапа.
 *
 * Скрипт вынимает строки прямо из исходников сборщика и сайта и требует
 * перевода для каждой — на английский и казахский.
 *
 * Запуск из каталога web:
 *     node --experimental-strip-types scripts/check-worker-text.mjs
 */
import fs from "node:fs";
import path from "node:path";

const WEB = path.resolve(import.meta.dirname, "..");
const WORKER = path.resolve(WEB, "..", "worker");
const { progressText, failureText, degradedText } = await import(
  path.join(WEB, "app/lib/worker-text.ts")
);

const read = (p) => fs.readFileSync(p, "utf8");
const pipeline = read(path.join(WORKER, "pipeline.py"));
const main = read(path.join(WORKER, "main.py"));
const script = read(path.join(WORKER, "steps/script_step.py"));
const projectsApi = read(path.join(WEB, "app/api/projects/route.ts"));
const retryApi = read(path.join(WEB, "app/api/projects/[id]/retry/route.ts"));

/** f-строку превращаем в образец с числами вместо подстановок. */
const sample = (s) => s.replace(/\{[^}]+\}/g, "3");
const cyr = /[А-Яа-яЁё]/;

const progress = new Set();
for (const m of pipeline.matchAll(/set_progress\(\s*[^,]+,\s*f?"([^"]+)"/g)) progress.add(sample(m[1]));
for (const m of pipeline.matchAll(/status_detail="([^"]+)"/g)) progress.add(m[1]);
for (const m of main.matchAll(/set_progress\([^,]+,\s*"([^"]+)"/g)) progress.add(m[1]);
for (const m of (projectsApi + retryApi).matchAll(/status_detail: "([^"]+)"/g)) progress.add(m[1]);

const failures = new Set();
for (const m of main.matchAll(/error_message="([^"]+)"/g)) failures.add(m[1]);
for (const m of script.matchAll(/ScriptRefusedError\("([^"]+)"\)/g)) failures.add(m[1]);
for (const m of (projectsApi + retryApi).matchAll(/(?:failProject\([^,]+,[^,]+,\s*|error_message: )"([^"]+)"/g)) failures.add(m[1]);

const degraded = new Set();
const reasonFn = pipeline.slice(pipeline.indexOf("def _degraded_reason"), pipeline.indexOf("def run_project"));
for (const m of reasonFn.matchAll(/return "([^"]+)"/g)) degraded.add(m[1]);

const groups = [
  ["ход работы", progress, progressText],
  ["причины отказа", failures, failureText],
  ["оговорки", degraded, degradedText],
];

let missing = 0;
let total = 0;
for (const [label, strings, fn] of groups) {
  console.log(`\n${label}:`);
  for (const text of [...strings].filter((s) => cyr.test(s)).sort()) {
    total++;
    const en = fn(text, "en");
    const kk = fn(text, "kk");
    const ok = en !== null && kk !== null;
    if (!ok) missing++;
    console.log(`  ${ok ? "✓" : "✗"} ${text}${ok ? `  →  ${en}` : "  — НЕТ ПЕРЕВОДА"}`);
  }
}
console.log(missing === 0 ? `\nВСЕ ${total} СТРОК ПЕРЕВЕДЕНЫ` : `\nБЕЗ ПЕРЕВОДА: ${missing} из ${total}`);
process.exit(missing === 0 ? 0 : 1);
