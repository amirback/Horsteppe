// Поведение опроса: счёт запросов при видимой вкладке, при скрытой, после 404.
import { launch, openPage, evaluate, sleep } from "./cdp.mjs";
const BASE = process.env.BASE ?? "http://localhost:3456";
// Одноразовый аккаунт: создайте его через /api/auth/signup и удалите после.
const email = process.env.QA_EMAIL;
const password = process.env.QA_PASS;
if (!email || !password) throw new Error("нужны QA_EMAIL и QA_PASS");
const ID = "00000000-0000-4000-8000-00000000abcd";
const check = (ok, label, extra = "") => console.log(`${ok ? "✓" : "✗"} ${label}${extra ? "  — " + extra : ""}`);
const { proc } = await launch();
try {
  const page = await openPage();
  await page.send("Page.enable");
  await page.send("Runtime.enable");
  await page.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
  // Вход.
  await page.send("Page.navigate", { url: `${BASE}/ru/login` });
  await sleep(2500);
  await evaluate(page, `(() => {
    const set = (el, v) => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set.call(el, v); el.dispatchEvent(new Event("input", { bubbles: true })); };
    set(document.querySelector("#email"), ${JSON.stringify(email)}); set(document.querySelector("#password"), ${JSON.stringify(password)});
    document.querySelector("form button[type=submit]").click();
  })()`);
  await sleep(4000);

  // Подмена ответа API: проект «в работе». Ничего не создаётся и не тратится.
  let mode = "generating";
  let hits = 0;
  await page.send("Fetch.enable", { patterns: [{ urlPattern: `*/api/projects/${ID}` }] });
  page.on(async (m) => {
    if (m.method !== "Fetch.requestPaused") return;
    hits++;
    const body = mode === "404"
      ? { error: "not_found" }
      : { project: { id: ID, topic: "Проверка опроса", style: "cinematic", duration_sec: 30, aspect_ratio: "9:16",
          status: "generating", status_detail: "Кадры: 2/8", error_message: null, real_video_coverage: null, degraded_reason: null },
          scenes: [], render: null };
    await page.send("Fetch.fulfillRequest", {
      requestId: m.params.requestId, responseCode: mode === "404" ? 404 : 200,
      responseHeaders: [{ name: "Content-Type", value: "application/json" }],
      body: Buffer.from(JSON.stringify(body)).toString("base64"),
    });
  });
  // Управляемая видимость вкладки.
  await page.send("Page.addScriptToEvaluateOnNewDocument", { source: `
    Object.defineProperty(document, "hidden", { configurable: true, get: () => window.__hidden === true });
    window.__setHidden = (v) => { window.__hidden = v; document.dispatchEvent(new Event("visibilitychange")); };` });

  await page.send("Page.navigate", { url: `${BASE}/ru/projects/${ID}` });
  await sleep(1500);
  const detail = await evaluate(page, `document.querySelector("main")?.innerText.includes("Кадры: 2/8")`);
  check(detail, "страница показывает ход работы из ответа");

  hits = 0; await sleep(9500);
  const visible = hits;
  check(visible >= 3 && visible <= 4, "видимая вкладка: опрос раз в 3 с", `${visible} запросов за 9.5 с`);

  await evaluate(page, "window.__setHidden(true)");
  await sleep(500); hits = 0; await sleep(12000);
  check(hits === 0, "скрытая вкладка: опрос спит", `${hits} запросов за 12 с`);

  hits = 0;
  await evaluate(page, "window.__setHidden(false)");
  await sleep(700);
  check(hits >= 1, "вкладку открыли — опрос проснулся сразу", `${hits} запрос(а) за 0.7 с`);

  mode = "404";
  await sleep(3500); hits = 0; await sleep(10000);
  check(hits === 0, "после 404 опрос остановился", `${hits} запросов за 10 с`);

  // Уход со страницы: опрос не должен продолжаться.
  mode = "generating";
  await page.send("Page.navigate", { url: `${BASE}/ru/projects/${ID}` });
  await sleep(2000);
  await evaluate(page, `document.querySelector('header a[href="/ru/pricing"]').click()`);
  await sleep(1500); hits = 0; await sleep(8000);
  const path = await evaluate(page, "location.pathname");
  check(path === "/ru/pricing" && hits === 0, "ушли со страницы проекта — опрос прекратился", `${hits} запросов за 8 с на ${path}`);
  page.close();
} finally { proc.kill(); }
