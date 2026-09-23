// Форма создания ролика: превью фото, бюджет, черновик при уходе на вход.
import path from "node:path";
import { launch, openPage, evaluate, sleep } from "./cdp.mjs";
const BASE = process.env.BASE ?? "http://localhost:3456";
const HERE = path.dirname(new URL(import.meta.url).pathname);
const check = (ok, label, extra = "") => console.log(`${ok ? "✓" : "✗"} ${label}${extra ? "  — " + extra : ""}`);
const { proc } = await launch();
try {
  const page = await openPage();
  await page.send("Page.enable"); await page.send("Runtime.enable"); await page.send("DOM.enable");
  await page.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 1000, deviceScaleFactor: 1, mobile: false });
  await page.send("Page.navigate", { url: `${BASE}/ru` });
  await sleep(2500);
  const clickText = (t) => evaluate(page, `[...document.querySelectorAll("button")].find(b => b.textContent.trim() === ${JSON.stringify(t)})?.click()`);
  const setFiles = async (file) => {
    const doc = await page.send("DOM.getDocument", { depth: -1 });
    const { nodeId } = await page.send("DOM.querySelector", { nodeId: doc.root.nodeId, selector: "input[type=file]" });
    await page.send("DOM.setFileInputFiles", { nodeId, files: [path.join(HERE, file)] });
  };
  const previews = () => evaluate(page, `[...document.querySelectorAll("img[src^='blob:']")].map(i => i.complete && i.naturalWidth > 0)`);

  // 1. Превью переживают вторую фотографию и переключение режима.
  await clickText("Реклама товара"); await sleep(400);
  await setFiles("p1.png"); await sleep(500);
  await setFiles("p2.png"); await sleep(700);
  let shown = await previews();
  check(shown.length === 2 && shown.every(Boolean), "две фотографии — оба превью видны", JSON.stringify(shown));
  await clickText("Ролик по описанию"); await sleep(400);
  await clickText("Реклама товара"); await sleep(900);
  shown = await previews();
  check(shown.length === 2 && shown.every(Boolean), "после смены режима туда и обратно превью живы", JSON.stringify(shown));

  // 2. Мусор в бюджете — отказ до отправки.
  const setField = (placeholderOrLabel, value) => evaluate(page, `(() => {
    const label = [...document.querySelectorAll("label")].find(l => l.querySelector("span")?.textContent.trim().startsWith(${JSON.stringify(placeholderOrLabel)}));
    const input = label.querySelector("input");
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set.call(input, ${JSON.stringify(value)});
    input.dispatchEvent(new Event("input", { bubbles: true }));
  })()`);
  const labels = await evaluate(page, `[...document.querySelectorAll("label span")].map(s => s.textContent.trim())`);
  const nameLabel = labels.find((l) => /назван/i.test(l));
  const budgetLabel = labels.find((l) => /бюджет|потол/i.test(l));
  await setField(nameLabel, "Войаж");
  await setField(budgetLabel, "abc");
  let requests = 0;
  await page.send("Network.enable");
  page.on((m) => { if (m.method === "Network.requestWillBeSent" && /\/api\//.test(m.params.request.url)) requests++; });
  await clickText("Создать рекламу") || await evaluate(page, `[...document.querySelectorAll("button")].find(b => /реклам/i.test(b.textContent) && b.className.includes("bg-ink") && b.textContent.includes("→") === false)?.click()`);
  await evaluate(page, `[...document.querySelectorAll("button.nav-link")].find(b => b.closest(".rounded-\\\\[28px\\\\]") && !b.disabled && b.querySelector("svg"))?.click()`);
  await sleep(800);
  const alert = await evaluate(page, `document.querySelector("[role=alert]")?.textContent ?? ""`);
  check(/0 до 20|число/i.test(alert) && requests === 0, "бюджет «abc» — отказ до отправки", `${alert} · запросов к API: ${requests}`);

  // 3. «1,5» принят, сервер ответил «не вошли» — черновик сохранён, человек на входе.
  await setField(budgetLabel, "1,5");
  await evaluate(page, `[...document.querySelectorAll("button.nav-link")].find(b => b.closest(".rounded-\\\\[28px\\\\]") && !b.disabled && b.querySelector("svg"))?.click()`);
  await sleep(4000);
  const at = await evaluate(page, "location.pathname");
  const draft = await evaluate(page, `sessionStorage.getItem("horsteppe-draft")`);
  const parsed = draft ? JSON.parse(draft) : {};
  check(at === "/ru/login" && parsed.budget === "1,5" && parsed.name === "Войаж" && parsed.mode === "product_ad",
    "бюджет «1,5» принят; без входа — на вход, черновик сохранён", `${at} · черновик: ${draft ? "есть" : "нет"}`);

  // 4. Вернулись на главную — форма восстановлена.
  await page.send("Page.navigate", { url: `${BASE}/ru` });
  await sleep(2500);
  const restored = await evaluate(page, `({
    mode: [...document.querySelectorAll("button[aria-pressed=true]")].map(b => b.textContent.trim()),
    inputs: [...document.querySelectorAll("label input")].map(i => i.value).filter(Boolean),
    left: sessionStorage.getItem("horsteppe-draft"),
  })`);
  check(restored.mode.includes("Реклама товара") && restored.inputs.includes("Войаж") && restored.inputs.includes("1,5") && restored.left === null,
    "после возврата форма восстановлена, черновик израсходован", JSON.stringify(restored.inputs));
  page.close();
} finally { proc.kill(); }
