import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { isBackendReady } from "@/lib/supabase/env";
import { isAdminEmail, isMissingSchema, paymentDetails } from "@/lib/credits";

/**
 * Кабинет: кредиты, заказы, история движений и пакеты на продажу.
 *
 * Читается пользовательским клиентом: политики базы отдают только свои
 * строки. `enabled: false` — миграция 0007 ещё не применена, сайт работает
 * без кредитов, как раньше.
 */
export async function GET() {
  if (!isBackendReady()) {
    return NextResponse.json({ error: "backend_not_configured" }, { status: 503 });
  }
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const [balances, orders, ledger, packages] = await Promise.all([
    supabase.from("credit_balances").select("tier, video_sec, available, reserved").order("video_sec"),
    supabase
      .from("orders")
      .select("id, package_id, tier, videos, video_sec, amount_kzt, status, created_at, paid_at")
      .order("created_at", { ascending: false })
      .limit(20),
    supabase
      .from("credit_ledger")
      .select("id, tier, video_sec, delta_available, kind, project_id, created_at")
      .order("created_at", { ascending: false })
      .limit(50),
    supabase
      .from("packages")
      .select("id, tier, videos, video_sec, price_kzt")
      .order("sort_order"),
  ]);

  const failed = [balances, orders, ledger, packages].find((r) => r.error);
  if (failed?.error) {
    if (isMissingSchema(failed.error)) {
      return NextResponse.json({ enabled: false, admin: isAdminEmail(user.email) });
    }
    console.error("account query failed:", failed.error.message);
    return NextResponse.json({ error: "query_failed" }, { status: 500 });
  }

  return NextResponse.json({
    enabled: true,
    admin: isAdminEmail(user.email),
    balances: balances.data ?? [],
    orders: orders.data ?? [],
    ledger: ledger.data ?? [],
    packages: packages.data ?? [],
    payment_details: paymentDetails(),
  });
}
