import { NextResponse } from "next/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { isAdminReady } from "@/lib/supabase/env";

const MIN_PASSWORD = 6;
const MAX_EMAIL = 254;

/**
 * Регистрация без письма-подтверждения.
 *
 * Обычный `auth.signUp` из браузера отправляет письмо через встроенную почту
 * Supabase, а она ограничена несколькими письмами в час на весь проект: уже
 * второй человек в мире получал «email rate limit exceeded» и завести аккаунт
 * не мог. Поэтому пользователь создаётся служебным ключом сразу подтверждённым,
 * а сессию клиент получает обычным входом по паролю.
 *
 * Когда появится свой домен и почтовый провайдер, подтверждение вернём —
 * этот маршрут тогда станет тонкой обёрткой над `signUp`.
 */
export async function POST(request: Request) {
  if (!isAdminReady()) {
    return NextResponse.json({ error: "backend_not_configured" }, { status: 503 });
  }

  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return NextResponse.json({ error: "invalid_request" }, { status: 400 });
  }

  const body = payload as { email?: unknown; password?: unknown };
  const email = typeof body.email === "string" ? body.email.trim().toLowerCase() : "";
  const password = typeof body.password === "string" ? body.password : "";

  if (!email || email.length > MAX_EMAIL || !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) {
    return NextResponse.json({ error: "invalid_email" }, { status: 400 });
  }
  if (password.length < MIN_PASSWORD) {
    return NextResponse.json({ error: "weak_password" }, { status: 400 });
  }

  const admin = createAdminClient();
  const { error } = await admin.auth.admin.createUser({
    email,
    password,
    email_confirm: true,
  });

  if (error) {
    // Supabase отвечает по-разному на занятый адрес в зависимости от версии,
    // поэтому проверяем и статус, и текст.
    const taken = error.status === 422 || /already|registered|exists/i.test(error.message ?? "");
    return NextResponse.json(
      { error: taken ? "email_taken" : "signup_failed" },
      { status: taken ? 409 : 500 }
    );
  }

  return NextResponse.json({ ok: true }, { status: 201 });
}
