"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import type { Lang } from "../lib/i18n";
import { CONTACT_EMAIL } from "../lib/content";
import { studio } from "../lib/studio-content";
import { account, orderCode, tenge, type Tier } from "../lib/account-content";
import { when } from "../lib/format";
import { Nav } from "./Nav";
import { Ambience } from "./Ambience";
import { Footer } from "./Footer";

type Balance = { tier: Tier; video_sec: number; available: number; reserved: number };
type Pkg = { id: string; tier: Tier; videos: number; video_sec: number; price_kzt: number };
type Order = {
  id: string; package_id: string; tier: Tier; videos: number; video_sec: number;
  amount_kzt: number; status: "pending" | "paid" | "canceled"; created_at: string;
};
type Move = {
  id: number; tier: Tier; video_sec: number; delta_available: number;
  kind: "purchase" | "reserve" | "spend" | "release"; project_id: string | null; created_at: string;
};
type Data = {
  enabled: boolean; admin: boolean; balances?: Balance[]; packages?: Pkg[];
  orders?: Order[]; ledger?: Move[]; payment_details?: string | null;
};

const TIER_ORDER: Tier[] = ["economy", "medium", "premium"];

/**
 * Кабинет: путь «купил пакет → оплатил → получил кредиты → заказал ролик».
 * Кредиты зачисляются только после подтверждённой оплаты.
 */
export function Account({ lang }: { lang: Lang }) {
  const a = account[lang];
  const s = studio[lang];
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [buying, setBuying] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await fetch("/api/account", { cache: "no-store" });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(s.errors[body.error ?? "unknown"] ?? s.errors.unknown);
        return;
      }
      setData(body);
      setError(null);
    } catch {
      setError(s.errors.network);
    }
  }, [s]);

  useEffect(() => {
    void load();
  }, [load]);

  async function buy(pkg: Pkg) {
    setBuying(pkg.id);
    try {
      const res = await fetch("/api/orders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ package_id: pkg.id }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(a.errors[body.error] ?? s.errors[body.error] ?? s.errors.unknown);
        return;
      }
      await load();
      document.getElementById("orders")?.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch {
      setError(s.errors.network);
    } finally {
      setBuying(null);
    }
  }

  const balances = (data?.balances ?? []).filter((b) => b.available > 0 || b.reserved > 0);
  const packages = data?.packages ?? [];
  const pending = (data?.orders ?? []).filter((o) => o.status === "pending");

  return (
    <>
      <Ambience />
      <Nav lang={lang} />

      <main className="container-x min-h-[70svh] pb-16 pt-28 md:pb-20 md:pt-36">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <h1 className="font-display text-[28px] font-bold tracking-[-0.025em] text-ink md:text-[38px]">{a.title}</h1>
          {data?.admin ? (
            <Link href={`/${lang}/admin`} className="nav-link rounded-full border border-ink/20 px-5 py-2.5 text-ink transition hover:border-ink/45">
              {a.adminLink}
            </Link>
          ) : null}
        </div>

        {error ? (
          <p role="alert" className="mt-8 rounded-2xl border border-ember/40 bg-white/60 px-5 py-4 text-[14.5px] text-ember">
            {error}
          </p>
        ) : null}

        {!data && !error ? <div className="mt-10 h-32 animate-pulse rounded-2xl bg-ink/5" /> : null}

        {data && !data.enabled ? (
          <p className="mt-8 rounded-2xl border border-ink/12 bg-white/45 px-5 py-6 text-[14.5px] text-ink-soft/80">{a.disabled}</p>
        ) : null}

        {data?.enabled ? (
          <>
            <section className="mt-8" aria-labelledby="balance">
              <h2 id="balance" className="font-display text-[19px] font-bold text-ink">{a.balanceTitle}</h2>
              {balances.length === 0 ? (
                <p className="mt-3 text-[14.5px] text-ink-soft/80">{a.balanceEmpty}</p>
              ) : (
                <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {balances.map((b) => (
                    <div key={`${b.tier}-${b.video_sec}`} className="rounded-2xl border border-sage/50 bg-sage/12 p-5">
                      <div className="text-[13px] text-ink-soft/70">{a.tiers[b.tier]} · {a.upTo(b.video_sec)}</div>
                      <div className="font-display mt-1 text-[30px] font-bold text-forest">{b.available}</div>
                      <div className="text-[12.5px] text-ink-soft/65">
                        {a.available}{b.reserved > 0 ? ` · ${a.inWork}: ${b.reserved}` : ""}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section className="mt-12" aria-labelledby="packages">
              <h2 id="packages" className="font-display text-[19px] font-bold text-ink">{a.packagesTitle}</h2>
              {packages.length === 0 ? <p className="mt-3 text-[14.5px] text-ink-soft/80">{a.packagesEmpty}</p> : null}
              {TIER_ORDER.filter((tier) => packages.some((p) => p.tier === tier)).map((tier) => (
                <div key={tier} className="mt-5">
                  <div className="text-[14px] font-medium text-ink">
                    {a.tiers[tier]} <span className="font-normal text-ink-soft/65">— {a.tierHints[tier]}</span>
                  </div>
                  <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    {packages.filter((p) => p.tier === tier).map((p) => (
                      <div key={p.id} className="flex flex-col rounded-2xl border border-ink/12 bg-white/45 p-5">
                        <div className="text-[14px] text-ink">{a.packageLine(p.videos, p.video_sec)}</div>
                        <div className="font-display mt-2 text-[22px] font-bold text-ink">{tenge(p.price_kzt)}</div>
                        <div className="text-[12.5px] text-ink-soft/60">{a.perVideo(tenge(p.price_kzt / p.videos))}</div>
                        <button
                          type="button"
                          disabled={buying !== null}
                          onClick={() => buy(p)}
                          className="nav-link mt-4 rounded-full bg-ink px-5 py-2.5 text-cream transition hover:bg-forest disabled:opacity-60"
                        >
                          {buying === p.id ? a.buying : a.buy}
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </section>

            <section id="orders" className="mt-12 scroll-mt-28" aria-labelledby="orders-title">
              <h2 id="orders-title" className="font-display text-[19px] font-bold text-ink">{a.ordersTitle}</h2>
              {pending.length > 0 ? (
                <div className="mt-4 rounded-2xl border border-ink/15 bg-white/60 p-5 text-[14px] leading-relaxed text-ink-soft">
                  <div className="font-medium text-ink">{a.payTitle}</div>
                  {pending.map((o) => (
                    <p key={o.id} className="mt-2">
                      {data.payment_details
                        ? a.payByDetails(tenge(o.amount_kzt), orderCode(o.id))
                        : a.payByMail(tenge(o.amount_kzt), orderCode(o.id), CONTACT_EMAIL)}
                    </p>
                  ))}
                  {data.payment_details ? (
                    <p className="mt-3 whitespace-pre-wrap rounded-xl bg-ink/5 px-4 py-3 text-ink">{data.payment_details}</p>
                  ) : null}
                  <p className="mt-3 text-[13px] text-ink-soft/70">{a.payAfter}</p>
                </div>
              ) : null}
              <div className="mt-4 grid gap-2">
                {(data.orders ?? []).map((o) => (
                  <div key={o.id} className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-ink/12 bg-white/45 px-5 py-3 text-[13.5px]">
                    <span className="text-ink">
                      {a.orderNo} {orderCode(o.id)} · {a.tiers[o.tier]} · {a.packageLine(o.videos, o.video_sec)}
                    </span>
                    <span className="text-ink-soft/70">
                      {tenge(o.amount_kzt)} · {a.orderStatus[o.status]} · {when(o.created_at, lang)}
                    </span>
                  </div>
                ))}
              </div>
            </section>

            <section className="mt-12" aria-labelledby="history">
              <h2 id="history" className="font-display text-[19px] font-bold text-ink">{a.historyTitle}</h2>
              {(data.ledger ?? []).length === 0 ? (
                <p className="mt-3 text-[14.5px] text-ink-soft/80">{a.historyEmpty}</p>
              ) : (
                <div className="mt-4 grid gap-2">
                  {(data.ledger ?? []).map((m) => (
                    <div key={m.id} className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-ink/10 bg-white/40 px-5 py-3 text-[13.5px]">
                      <span className="text-ink">
                        {a.kinds[m.kind]} · {a.tiers[m.tier]} · {a.upTo(m.video_sec)}
                        {m.project_id ? (
                          <Link href={`/${lang}/projects/${m.project_id}`} className="ml-2 underline decoration-ink/30 underline-offset-2">→</Link>
                        ) : null}
                      </span>
                      <span className="text-ink-soft/70">
                        {m.delta_available > 0 ? `+${m.delta_available}` : m.delta_available || "·"} · {when(m.created_at, lang)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </>
        ) : null}
      </main>

      <Footer lang={lang} />
    </>
  );
}
