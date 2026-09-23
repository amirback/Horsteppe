// Что видно до загрузки JavaScript: скрипты отключены, считаем невидимые блоки.
import fs from "node:fs";
import { launch, openPage, evaluate, sleep } from "./cdp.mjs";
const BASE = process.env.BASE ?? "http://localhost:3456";
const OUT = process.argv[2] ?? "nojs";
fs.mkdirSync(OUT, { recursive: true });
const { proc } = await launch();
try {
  for (const url of (process.env.PAGES ?? "/ru,/ru/terms,/ru/pricing").split(",")) {
    const page = await openPage();
    await page.send("Page.enable");
    await page.send("Emulation.setScriptExecutionDisabled", { value: true });
    await page.send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
    await page.send("Page.navigate", { url: BASE + url });
    await sleep(2500);
    // Скрипты отключены — считаем через DOM-запрос самого протокола.
    const doc = await page.send("DOM.getDocument", { depth: -1 });
    const found = await page.send("DOM.querySelectorAll", { nodeId: doc.root.nodeId, selector: "[style*='opacity:0']" });
    const h1 = await page.send("DOM.querySelector", { nodeId: doc.root.nodeId, selector: "h1" });
    let h1Hidden = false;
    if (h1.nodeId) {
      const html = (await page.send("DOM.getOuterHTML", { nodeId: h1.nodeId })).outerHTML;
      h1Hidden = /opacity:0/.test(html);
    }
    const shot = await page.send("Page.captureScreenshot", { format: "png" });
    fs.writeFileSync(`${OUT}/${url.replace(/\//g, "_")}.png`, Buffer.from(shot.data, "base64"));
    console.log(`${url.padEnd(12)} блоков с opacity:0 до загрузки JS: ${String(found.nodeIds.length).padStart(3)}   заголовок внутри скрыт: ${h1Hidden ? "ДА" : "нет"}`);
    page.close();
  }
} finally { proc.kill(); }
