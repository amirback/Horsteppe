// Сквозной прогон со входом: форма входа → шапка на статичных страницах → API.
import { launch, openPage, evaluate, sleep } from "./cdp.mjs";
const BASE = process.env.BASE ?? "http://localhost:3456";
// Одноразовый аккаунт: создайте его через /api/auth/signup и удалите после.
const email = process.env.QA_EMAIL;
const password = process.env.QA_PASS;
if (!email || !password) throw new Error("нужны QA_EMAIL и QA_PASS");
const { proc } = await launch();
const check = (ok, label, extra = "") => console.log(`${ok ? "✓" : "✗"} ${label}${extra ? "  — " + extra : ""}`);
try {
  const page = await openPage();
  const errors = [];
  page.on((m) => {
    if (m.method === "Runtime.exceptionThrown") errors.push(m.params.exceptionDetails.exception?.description?.split("\n")[0]);
    if (m.method === "Runtime.consoleAPICalled" && m.params.type === "error") errors.push(m.params.args.map((a) => a.value ?? a.description).join(" ").slice(0, 150));
  });
  await page.send("Runtime.enable");
  await page.send("Page.enable");
  await page.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });

  // 1. Гость: шапка без аватара, со ссылкой «Войти».
  await page.send("Page.navigate", { url: `${BASE}/ru/pricing` });
  await sleep(2500);
  let head = await evaluate(page, `({ login: !!document.querySelector('header a[href="/ru/login"]'), avatar: !!document.querySelector('header button[aria-haspopup="menu"]') })`);
  check(head.login && !head.avatar, "гость видит «Войти» и не видит аватар");

  // 2. Закрытая страница без входа уводит на вход с адресом возврата.
  await page.send("Page.navigate", { url: `${BASE}/ru/projects` });
  await sleep(2000);
  const redirected = await evaluate(page, "location.pathname + location.search");
  check(redirected.startsWith("/ru/login?next=%2Fru%2Fprojects"), "гостя с «Моих видео» уводит на вход", redirected);

  // 3. Вход через настоящую форму.
  await evaluate(page, `(() => {
    const set = (el, v) => { const s = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set; s.call(el, v); el.dispatchEvent(new Event("input", { bubbles: true })); };
    set(document.querySelector("#email"), ${JSON.stringify(email)});
    set(document.querySelector("#password"), ${JSON.stringify(password)});
    document.querySelector("form button[type=submit]").click();
  })()`);
  await sleep(4000);
  const after = await evaluate(page, "location.pathname");
  check(after === "/ru/projects", "после входа вернуло туда, откуда увели", after);

  // 4. Список проектов: пустое состояние, без ошибки.
  await sleep(1500);
  const list = await evaluate(page, `({ empty: document.body.innerText.includes("${"Пока"}") || !!document.querySelector("main a[href='/ru#top']"), alert: document.querySelector("[role=alert]")?.textContent ?? null })`);
  check(!list.alert, "«Мои видео» открылись без ошибки", list.alert ?? "");

  // 5. Статичная страница знает о входе: аватар в шапке.
  await page.send("Page.navigate", { url: `${BASE}/ru/pricing` });
  await sleep(2500);
  head = await evaluate(page, `({ login: !!document.querySelector('header a[href="/ru/login"]'), avatar: document.querySelector('header button[aria-haspopup="menu"]')?.title ?? null })`);
  check(!head.login && head.avatar === email, "на статичной странице тарифов — аватар вошедшего", head.avatar ?? "аватара нет");

  // 6. API с сессией: мусорный id и чужой/несуществующий проект.
  const api = await evaluate(page, `(async () => {
    const r1 = await fetch("/api/projects/not-a-uuid"); const r2 = await fetch("/api/projects/00000000-0000-4000-8000-000000000000");
    const r3 = await fetch("/api/projects/not-a-uuid/retry", { method: "POST" }); const r4 = await fetch("/api/projects");
    const list = await r4.json();
    return { bad: [r1.status, (await r1.json()).error], missing: [r2.status, (await r2.json()).error], retry: [r3.status, (await r3.json()).error], list: [r4.status, list.counts] };
  })()`);
  check(api.bad[0] === 404 && api.bad[1] === "not_found", "мусорный id → 404, а не «ошибка запроса»", JSON.stringify(api.bad));
  check(api.missing[0] === 404, "несуществующий проект → 404", JSON.stringify(api.missing));
  check(api.retry[0] === 404, "повтор с мусорным id → 404", JSON.stringify(api.retry));
  check(api.list[0] === 200, "список проектов через API", JSON.stringify(api.list));

  // 7. Меню пользователя закрывается касанием мимо (pointerdown).
  await evaluate(page, `document.querySelector('header button[aria-haspopup="menu"]').click()`);
  await sleep(400);
  const opened = await evaluate(page, `!!document.querySelector('[role=menu]')`);
  await page.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x: 640, y: 700 }] });
  await page.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
  await sleep(400);
  const closed = !(await evaluate(page, `!!document.querySelector('[role=menu]')`));
  check(opened && closed, "меню пользователя закрывается касанием мимо");

  // 8. Выход меняет шапку.
  await evaluate(page, `document.querySelector('header button[aria-haspopup="menu"]').click()`);
  await sleep(300);
  await evaluate(page, `[...document.querySelectorAll('[role=menuitem]')].pop().click()`);
  await sleep(3000);
  head = await evaluate(page, `({ login: !!document.querySelector('header a[href="/ru/login"]'), avatar: !!document.querySelector('header button[aria-haspopup="menu"]'), path: location.pathname })`);
  check(head.login && !head.avatar, "после выхода шапка снова гостевая", head.path);

  check(errors.length === 0, "ошибок в консоли нет", [...new Set(errors)].join(" | "));
  page.close();
} finally { proc.kill(); }
