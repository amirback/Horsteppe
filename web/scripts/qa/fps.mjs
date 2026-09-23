// Частота кадров и длинные кадры при замедленном процессоре.
import { launch, openPage, evaluate, sleep } from "./cdp.mjs";
const BASE = process.env.BASE ?? "http://localhost:3456";
const PAGES = (process.env.PAGES ?? "/ru,/ru/terms").split(",");
const RUNS = Number(process.env.RUNS ?? 3);
const { proc } = await launch();
try {
  for (const url of PAGES) {
    const results = [];
    for (let run = 0; run < RUNS; run++) {
      const page = await openPage();
      await page.send("Page.enable");
      await page.send("Performance.enable");
      await page.send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 2, mobile: true });
      await page.send("Emulation.setCPUThrottlingRate", { rate: 4 });
      await page.send("Page.navigate", { url: BASE + url });
      await sleep(4000); // дать доиграть появлению, мерить установившийся фон
      const before = Object.fromEntries((await page.send("Performance.getMetrics")).metrics.map((m) => [m.name, m.value]));
      const r = await evaluate(page, `new Promise((done) => {
        const frames = []; let last = performance.now(); const start = last;
        function tick(t) { frames.push(t - last); last = t; if (t - start < 5000) requestAnimationFrame(tick); else done(frames); }
        requestAnimationFrame(tick);
      })`);
      const after = Object.fromEntries((await page.send("Performance.getMetrics")).metrics.map((m) => [m.name, m.value]));
      const fps = r.length / 5;
      const long = r.filter((d) => d > 50).length;
      const busy = (after.TaskDuration - before.TaskDuration) / 5; // доля секунды, занятая задачами главного потока
      results.push({ fps, long, busy });
      page.close();
    }
    const avg = (k) => results.reduce((s, x) => s + x[k], 0) / results.length;
    console.log(`${url.padEnd(10)} кадров/с ${avg("fps").toFixed(1).padStart(5)}   кадров >50 мс ${avg("long").toFixed(1).padStart(5)}   занятость главного потока ${(avg("busy") * 100).toFixed(0)}%   (прогонов: ${RUNS})`);
  }
} finally { proc.kill(); }
