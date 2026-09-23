// Прогон вёрстки: горизонтальная прокрутка, ошибки консоли, снимки экрана.
import fs from "node:fs";
import path from "node:path";
import { launch, openPage, evaluate, sleep } from "./cdp.mjs";

const BASE = process.env.BASE ?? "http://localhost:3456";
const OUT = process.argv[2] ?? "shots";
const PAGES = (process.env.PAGES ?? "/ru,/en/pricing,/kk/terms,/ru/login,/en/help").split(",");
const VIEWPORTS = [
  ["phone-360", 360, 740, true], ["phone-390", 390, 844, true], ["tablet-768", 768, 1024, true],
  ["laptop-1024", 1024, 768, false], ["desktop-1440", 1440, 900, false], ["ultrawide-2560", 2560, 1080, false],
];

fs.mkdirSync(OUT, { recursive: true });
const { proc } = await launch();
const report = [];
try {
  for (const url of PAGES) {
    for (const [name, width, height, mobile] of VIEWPORTS) {
      const page = await openPage();
      const errors = [];
      page.on((m) => {
        if (m.method === "Runtime.exceptionThrown") errors.push("исключение: " + (m.params.exceptionDetails.exception?.description ?? m.params.exceptionDetails.text).split("\n")[0]);
        if (m.method === "Runtime.consoleAPICalled" && m.params.type === "error")
          errors.push("console.error: " + m.params.args.map((a) => a.value ?? a.description ?? "").join(" ").slice(0, 160));
        if (m.method === "Log.entryAdded" && m.params.entry.level === "error" && !/favicon/.test(m.params.entry.url ?? ""))
          errors.push("лог: " + m.params.entry.text.slice(0, 160));
      });
      await page.send("Runtime.enable");
      await page.send("Log.enable");
      await page.send("Page.enable");
      await page.send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile });
      await page.send("Page.navigate", { url: BASE + url });
      await sleep(3500); // дать анимациям появления доиграть
      const layout = await evaluate(page, `(() => {
        const W = document.documentElement.clientWidth;
        const scrollW = document.documentElement.scrollWidth;
        const offenders = [];
        if (scrollW > W + 1) {
          for (const el of document.querySelectorAll("body *")) {
            const r = el.getBoundingClientRect();
            if (r.width && (r.right > W + 1)) {
              let p = el.parentElement, clipped = false;
              while (p) { const s = getComputedStyle(p); if (/(hidden|clip|auto|scroll)/.test(s.overflowX)) { clipped = true; break; } p = p.parentElement; }
              if (!clipped) offenders.push(el.tagName.toLowerCase() + " «" + (el.textContent||"").trim().slice(0,30) + "» до " + Math.round(r.right) + "px");
            }
          }
        }
        return { W, scrollW, offenders: offenders.slice(0, 5), h1: document.querySelector("h1")?.textContent?.trim().slice(0, 40) ?? "" };
      })()`);
      const shot = await page.send("Page.captureScreenshot", { format: "png" });
      const file = path.join(OUT, `${url.replace(/\//g, "_").replace(/^_/, "")}__${name}.png`);
      fs.writeFileSync(file, Buffer.from(shot.data, "base64"));
      report.push({ url, name, ...layout, errors });
      page.close();
    }
  }
} finally {
  proc.kill();
}

let problems = 0;
for (const r of report) {
  const overflow = r.scrollW > r.W + 1;
  const bad = overflow || r.errors.length;
  if (bad) problems++;
  console.log(`${bad ? "✗" : "✓"} ${r.url.padEnd(12)} ${r.name.padEnd(15)} ${overflow ? `ГОРИЗ. ПРОКРУТКА ${r.scrollW}>${r.W} ` + r.offenders.join("; ") : "без прокрутки"}${r.errors.length ? "  ОШИБКИ: " + [...new Set(r.errors)].join(" | ") : ""}`);
}
console.log(problems ? `\nПРОБЛЕМ: ${problems} из ${report.length}` : `\nВСЕ ${report.length} ПРОГОНОВ ЧИСТЫЕ`);
