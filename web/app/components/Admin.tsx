"use client";

import { useCallback, useEffect, useState } from "react";
import type { Lang } from "../lib/i18n";
import { account, orderCode, tenge, type Tier } from "../lib/account-content";
import { when } from "../lib/format";
import { Nav } from "./Nav";
import { Ambience } from "./Ambience";
import { Footer } from "./Footer";

type Order = {
  id: string; email: string | null; package_id: string; tier: Tier; videos: number; video_sec: number;
  amount_kzt: number; status: "pending" | "paid" | "canceled"; created_at: string; confirmed_by: string | null;
};
type Pkg = { id: string; tier: Tier; videos: number; video_sec: number; price_kzt: number; active: boolean; source: string | null };
type Data = { enabled: boolean; orders?: Order[]; packages?: Pkg[] };

/**
 * Касса основателя. Внутренний инструмент, поэтому только по-русски.
 * «Оплачено» зачисляет кредиты функцией базы: второе нажатие ничего не добавит.
 */
export function Admin({ lang }: { lang: Lang }) {
  const a = account.ru;
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [prices, setPrices] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    const res = await fetch("/api/admin", { cache: "no-store" }).catch(() => null);
    if (!res) return setError("Нет связи с сервером.");
    if (res.status === 401 || res.status === 403) return setError("Нет доступа: почты нет в ADMIN_EMAILS.");
    if (!res.ok) return setError("Не удалось загрузить кассу.");
    setData(await res.json());
    setError(null);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function act(payload: Record<string, unknown>, confirmText?: string) {
    if (confirmText && !window.confirm(confirmText)) return;
    setBusy(true);
    try {
      const res = await fetch("/api/admin", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) setError(`Не вышло: ${body.error ?? res.status}`);
      await load();
    } finally {
      setBusy(false);
    }
  }

  const orders = data?.orders ?? [];
  const pending = orders.filter((o) => o.status === "pending");
  const rest = orders.filter((o) => o.status !== "pending");

  return (
    <>
      <Ambience />
      <Nav lang={lang} />
      <main className="container-x min-h-[70svh] pb-16 pt-28 md:pt-36">
        <h1 className="font-display text-[28px] font-bold tracking-[-0.025em] text-ink md:text-[38px]">Касса</h1>
        {error ? <p role="alert" className="mt-6 rounded-2xl border border-ember/40 bg-white/60 px-5 py-4 text-[14.5px] text-ember">{error}</p> : null}
        {data && !data.enabled ? (
          <p className="mt-6 text-[14.5px] text-ink-soft">Миграция 0007 не применена: кредитов и заказов в базе ещё нет.</p>
        ) : null}

        {data?.enabled ? (
          <>
            <h2 className="font-display mt-8 text-[19px] font-bold text-ink">Ждут оплаты ({pending.length})</h2>
            <p className="mt-1 text-[13px] text-ink-soft/70">Сверьте поступление по почте покупателя и номеру заказа, затем нажмите «Оплачено».</p>
            <div className="mt-3 grid gap-2">
              {pending.map((o) => (
                <div key={o.id} className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-ink/15 bg-white/60 px-5 py-3 text-[13.5px]">
                  <span className="text-ink">
                    {orderCode(o.id)} · {o.email ?? "—"} · {o.package_id} ({a.tiers[o.tier]}, {a.packageLine(o.videos, o.video_sec)}) · <b>{tenge(o.amount_kzt)}</b> · {when(o.created_at, lang)}
                  </span>
                  <span className="flex gap-2">
                    <button type="button" disabled={busy}
                      onClick={() => act({ action: "confirm", order_id: o.id },
                        `Деньги ${tenge(o.amount_kzt)} по заказу ${orderCode(o.id)} пришли? Покупатель получит ${o.videos} кредитов.`)}
                      className="nav-link rounded-full bg-forest px-4 py-2 text-cream disabled:opacity-60">Оплачено</button>
                    <button type="button" disabled={busy}
                      onClick={() => act({ action: "cancel", order_id: o.id }, `Отменить заказ ${orderCode(o.id)}?`)}
                      className="nav-link rounded-full border border-ink/25 px-4 py-2 text-ink disabled:opacity-60">Отменить</button>
                  </span>
                </div>
              ))}
            </div>

            <h2 className="font-display mt-10 text-[19px] font-bold text-ink">Пакеты</h2>
            <p className="mt-1 text-[13px] text-ink-soft/70">
              Покупателям видны только включённые. Цены из КП 09.11 включают ручную работу; цена самостоятельной генерации от 14.11 ниже (docs/MONEY.md §8.1, §10).
            </p>
            <div className="mt-3 grid gap-2">
              {(data.packages ?? []).map((p) => (
                <div key={p.id} className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-ink/12 bg-white/45 px-5 py-3 text-[13.5px]">
                  <label className="flex items-center gap-2 text-ink">
                    <input type="checkbox" checked={p.active} disabled={busy}
                      onChange={(e) => act({ action: "package", package_id: p.id, active: e.target.checked })} />
                    {p.id} · {a.tiers[p.tier]} · {a.packageLine(p.videos, p.video_sec)}
                  </label>
                  <span className="flex items-center gap-2 text-ink-soft/70">
                    <input
                      inputMode="numeric"
                      value={prices[p.id] ?? String(p.price_kzt)}
                      onChange={(e) => setPrices({ ...prices, [p.id]: e.target.value.replace(/\D/g, "") })}
                      className="w-28 rounded-lg border border-ink/20 bg-white/70 px-2 py-1 text-right text-ink"
                      aria-label={`Цена ${p.id}`}
                    />
                    ₸
                    <button type="button" disabled={busy || !prices[p.id] || Number(prices[p.id]) === p.price_kzt}
                      onClick={() => act({ action: "package", package_id: p.id, price_kzt: Number(prices[p.id]) })}
                      className="nav-link rounded-full border border-ink/25 px-3 py-1.5 text-ink disabled:opacity-40">Сохранить</button>
                    <span className="text-[12px]">{p.source ?? ""}</span>
                  </span>
                </div>
              ))}
            </div>

            <h2 className="font-display mt-10 text-[19px] font-bold text-ink">Закрытые заказы</h2>
            <div className="mt-3 grid gap-2">
              {rest.map((o) => (
                <div key={o.id} className="rounded-2xl border border-ink/10 bg-white/40 px-5 py-3 text-[13px] text-ink-soft">
                  {orderCode(o.id)} · {o.email ?? "—"} · {o.package_id} · {tenge(o.amount_kzt)} · {a.orderStatus[o.status]}
                  {o.confirmed_by ? ` · ${o.confirmed_by}` : ""} · {when(o.created_at, lang)}
                </div>
              ))}
            </div>
          </>
        ) : null}
      </main>
      <Footer lang={lang} />
    </>
  );
}
