import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { isAdminReady } from "@/lib/supabase/env";
import { isMissingSchema } from "@/lib/credits";

/** Сколько неоплаченных заказов может висеть у человека одновременно. */
const MAX_PENDING = 3;

/**
 * Заказ пакета. Кредиты здесь НЕ зачисляются: только после подтверждённой
 * оплаты (админ или провайдер платежей) функцией grant_order_credits.
 *
 * Цена и состав берутся из базы, а не из запроса: клиент присылает только
 * код пакета, и подменить сумму ему нечем.
 */
export async function POST(request: Request) {
  if (!isAdminReady()) {
    return NextResponse.json({ error: "backend_not_configured" }, { status: 503 });
  }
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  let body: { package_id?: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "invalid_request" }, { status: 400 });
  }
  const packageId = String(body.package_id ?? "").trim();
  if (!/^[A-Za-z0-9_-]{1,32}$/.test(packageId)) {
    return NextResponse.json({ error: "package_not_found" }, { status: 404 });
  }

  const admin = createAdminClient();
  const { data: pkg, error: pkgError } = await admin
    .from("packages")
    .select("id, tier, videos, video_sec, price_kzt, active")
    .eq("id", packageId)
    .maybeSingle();
  if (pkgError) {
    if (isMissingSchema(pkgError)) {
      return NextResponse.json({ error: "credits_disabled" }, { status: 503 });
    }
    console.error("package lookup failed:", pkgError.message);
    return NextResponse.json({ error: "query_failed" }, { status: 500 });
  }
  if (!pkg || !pkg.active) {
    return NextResponse.json({ error: "package_not_found" }, { status: 404 });
  }

  const { count: pending } = await admin
    .from("orders")
    .select("id", { count: "exact", head: true })
    .eq("user_id", user.id)
    .eq("status", "pending");
  if ((pending ?? 0) >= MAX_PENDING) {
    return NextResponse.json({ error: "too_many_pending_orders", limit: MAX_PENDING }, { status: 429 });
  }

  const { data: order, error } = await admin
    .from("orders")
    .insert({
      user_id: user.id,
      email: user.email ?? null,
      package_id: pkg.id,
      tier: pkg.tier,
      videos: pkg.videos,
      video_sec: pkg.video_sec,
      amount_kzt: pkg.price_kzt,
    })
    .select("id")
    .single();
  if (error || !order) {
    console.error("order insert failed:", error?.message);
    return NextResponse.json({ error: "create_failed" }, { status: 500 });
  }
  return NextResponse.json({ id: order.id }, { status: 201 });
}
