/**
 * Сверка правил оценки ролика (app/lib/feedback.ts).
 *
 * Проверяет без сети и без базы: разбор того, что присылает браузер, сводку
 * провайдеров настоящих клипов, распознавание ещё не применённой миграции и
 * совпадение списка причин с проверкой таблицы в миграции 0006. Две копии
 * одного списка расходятся молча — запись тогда отвергнет сама база.
 *
 * Запуск из каталога web:
 *     node --experimental-strip-types scripts/check-feedback.mjs
 */
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const WEB = path.resolve(import.meta.dirname, "..");
const {
  parseFeedback, summarizeSources, isMissingTable, modelLabel, providerLabel,
  FEEDBACK_REASONS, MAX_COMMENT,
} = await import(path.join(WEB, "app/lib/feedback.ts"));

let passed = 0;
function check(label, fn) {
  fn();
  passed += 1;
  console.log(`✓ ${label}`);
}

check("хорошая оценка принимается без причин", () =>
  assert.deepEqual(parseFeedback({ rating: "good" }), { rating: "good", reasons: [], comment: null }));
check("у хорошей оценки причины отбрасываются", () =>
  assert.deepEqual(parseFeedback({ rating: "good", reasons: ["motion"] }).reasons, []));
check("«нужно улучшить» без причины не принимается", () =>
  assert.equal(parseFeedback({ rating: "needs_improvement", reasons: [] }), null));
check("неизвестная причина не принимается", () =>
  assert.equal(parseFeedback({ rating: "needs_improvement", reasons: ["motion", "hack"] }), null));
check("причины без повторов", () =>
  assert.deepEqual(
    parseFeedback({ rating: "needs_improvement", reasons: ["motion", "motion", "sound"] }).reasons,
    ["motion", "sound"],
  ));
check("комментарий обрезается, пустой становится null", () => {
  assert.equal(parseFeedback({ rating: "needs_improvement", reasons: ["other"], comment: "  мало движения  " }).comment,
    "мало движения");
  assert.equal(parseFeedback({ rating: "good", comment: "   " }).comment, null);
});
check("слишком длинный комментарий не принимается", () =>
  assert.equal(parseFeedback({ rating: "good", comment: "a".repeat(MAX_COMMENT + 1) }), null));
check("комментарий не строкой — отказ", () =>
  assert.equal(parseFeedback({ rating: "good", comment: { evil: true } }), null));
check("неизвестная оценка и мусор — отказ", () => {
  for (const raw of [null, "good", 1, [], {}, { rating: "great" }, { rating: "good", reasons: "motion" }]) {
    assert.equal(parseFeedback(raw), null, JSON.stringify(raw));
  }
});
check("сводка считает только настоящие клипы и сортирует по числу", () =>
  assert.deepEqual(summarizeSources([
    { provider: "higgsfield", model: "kling-video/v2.5-turbo/pro/image-to-video", generation_mode: "real_video" },
    { provider: "higgsfield", model: "kling-video/v2.5-turbo/standard/image-to-video", generation_mode: "real_video" },
    { provider: "higgsfield", model: "kling-video/v2.5-turbo/standard/image-to-video", generation_mode: "real_video" },
    { provider: "higgsfield", model: "kling-video/v2.5-turbo/pro/image-to-video", generation_mode: "image_motion" },
    { provider: null, model: null, generation_mode: "image_motion" },
  ]), [
    { provider: "higgsfield", model: "kling-video/v2.5-turbo/standard/image-to-video", shots: 2 },
    { provider: "higgsfield", model: "kling-video/v2.5-turbo/pro/image-to-video", shots: 1 },
  ]));
check("ещё не применённая миграция распознаётся, прочие сбои — нет", () => {
  assert.equal(isMissingTable({ code: "PGRST205", message: "Could not find the table 'public.project_feedback' in the schema cache" }), true);
  assert.equal(isMissingTable({ code: "42P01", message: "relation does not exist" }), true);
  assert.equal(isMissingTable({ code: "23505", message: "duplicate key" }), false);
  assert.equal(isMissingTable(null), false);
});
check("подписи провайдера и модели человеческие", () => {
  assert.equal(providerLabel("higgsfield"), "Higgsfield");
  assert.equal(modelLabel("kling-video/v2.5-turbo/pro/image-to-video"), "Kling 2.5 Turbo Pro");
  assert.equal(modelLabel("неизвестная/модель"), "неизвестная/модель");
});
check("список причин совпадает с проверкой таблицы в миграции 0006", () => {
  const sql = fs.readFileSync(
    path.join(WEB, "..", "supabase", "migrations", "0006_provider_requests_and_feedback.sql"), "utf8",
  );
  const block = sql.match(/reasons <@ array\[([\s\S]+?)\]::text\[\]/);
  assert.ok(block, "проверка причин в миграции не найдена");
  const listed = block[1].match(/'([a-z_]+)'/g).map((s) => s.slice(1, -1));
  assert.deepEqual(listed, [...FEEDBACK_REASONS]);
});

console.log(`\n${passed} проверок пройдено`);
