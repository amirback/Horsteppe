// Уважает ли сайт «уменьшить движение»: смотрим, меняется ли transform у анимированной стрелки.
import { launch, openPage, evaluate, sleep } from "./cdp.mjs";
const BASE = process.env.BASE ?? "http://localhost:3456";
const { proc } = await launch();
try {
  for (const reduce of [false, true]) {
    const page = await openPage();
    await page.send("Page.enable");
    await page.send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-reduced-motion", value: reduce ? "reduce" : "no-preference" }] });
    await page.send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
    await page.send("Page.navigate", { url: BASE + "/ru" });
    await sleep(3000);
    const sample = `(() => { const el = document.querySelector('a[href="#how"] span'); return el ? getComputedStyle(el).transform : "нет элемента"; })()`;
    const seen = new Set();
    for (let i = 0; i < 8; i++) { seen.add(await evaluate(page, sample)); await sleep(230); }
    console.log(`уменьшить движение: ${reduce ? "ВКЛ " : "выкл"}  → разных положений стрелки за 2 с: ${seen.size}${seen.size > 1 ? " (движется)" : " (стоит)"}`);
    page.close();
  }
} finally { proc.kill(); }
