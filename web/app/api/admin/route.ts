import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { isAdminReady } from "@/lib/supabase/env";
import { isAdminEmail, isMissingSchema } from "@/lib/credits";

/**
 * Касса основателя: заказы и пакеты.
 *
 * Доступ — только почтам из ADMIN_EMAILS. Кредиты зачисляет функция базы
 * grant_order_credits: второе нажатие «Оплачено» ничего не добавит.
 */
async function adminEmail(): Promise<string | null> {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  return user && isAdminEmail(user.email) ? (user.email as string) : null;
}

export async function GET() {
  if (!isAdminReady()) {
    return NextResponse.json({ error: "backend_not_configured" }, { status: 503 });
  }
  if (!(await adminEmail())) {
    return NextResponse.json({ error: "forbidden" }, { status: 403 });
  }
  const admin = createAdminClient();
  const [orders, packages] = await Promise.all([
    admin
      .from("orders")
      .select("id, email, package_id, tier, videos, video_sec, amount_kzt, status, provider, created_at, paid_at, confirmed_by")
      .order("created_at", { ascending: false })
      .limit(100),
    admin.from("packages").select("id, tier, videos, video_sec, price_kzt, active, source").order("sort_order"),
  ]);
  const failed = orders.error ?? packages.error;
  if (failed) {
    if (isMissingSchema(failed)) return NextResponse.json({ enabled: false });
    console.error("admin query failed:", failed.message);
    return NextResponse.json({ error: "query_failed" }, { status: 500 });
  }
  return NextResponse.json({ enabled: true, orders: orders.data ?? [], packages: packages.data ?? [] });
}

type Body = {
  action?: "confirm" | "cancel" | "package";
  order_id?: string;
  package_id?: string;
  active?: boolean;
  price_kzt?: number;
};

export async function POST(request: Request) {
  if (!isAdminReady()) {
    return NextResponse.json({ error: "backend_not_configured" }, { status: 503 });
  }
  const email = await adminEmail();
  if (!email) {
    return NextResponse.json({ error: "forbidden" }, { status: 403 });
  }
  let body: Body;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "invalid_request" }, { status: 400 });
  }
  const admin = createAdminClient();

  if (body.action === "confirm" && body.order_id) {
    const { data, error } = await admin.rpc("grant_order_credits", {
      p_order: body.order_id, p_provider: "manual", p_payment_id: null, p_amount_kzt: null,
      p_confirmed_by: email,
    });
    if (error) {
      console.error("grant failed:", error.message);
      return NextResponse.json({ error: "grant_failed" }, { status: 400 });
    }
    return NextResponse.json({ result: data });
  }

  if (body.action === "cancel" && body.order_id) {
    const { error } = await admin
      .from("orders")
      .update({ status: "canceled", confirmed_by: email })
      .eq("id", body.order_id)
      .eq("status", "pending"); // оплаченный заказ отменой не стереть
    if (error) return NextResponse.json({ error: "update_failed" }, { status: 500 });
    return NextResponse.json({ ok: true });
  }

  if (body.action === "package" && body.package_id) {
    const patch: Record<string, unknown> = { updated_at: new Date().toISOString() };
    if (typeof body.active === "boolean") patch.active = body.active;
    if (body.price_kzt !== undefined) {
      const price = Math.round(Number(body.price_kzt));
      if (!Number.isFinite(price) || price <= 0 || price > 10_000_000) {
        return NextResponse.json({ error: "invalid_price" }, { status: 400 });
      }
      patch.price_kzt = price;
      patch.source = `правка ${email} ${new Date().toISOString().slice(0, 10)}`;
    }
    const { error } = await admin.from("packages").update(patch).eq("id", body.package_id);
    if (error) return NextResponse.json({ error: "update_failed" }, { status: 500 });
    return NextResponse.json({ ok: true });
  }

  return NextResponse.json({ error: "invalid_request" }, { status: 400 });
}
