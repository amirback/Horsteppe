import { NextResponse } from "next/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { isAdminReady } from "@/lib/supabase/env";

// Восемь — общепринятый минимум. Шесть символов подбираются перебором за
// минуты. Уже заведённые аккаунты это не затрагивает: проверка стоит только
// на регистрации, вход принимает любой прежний пароль.
const MIN_PASSWORD = 8;
// Supabase хранит пароль в bcrypt, а bcrypt читает только первые 72 байта.
// Длиннее — провайдер отвечает ошибкой, и человек видел «не удалось
// зарегистрироваться» без объяснения. Считаем именно байты: кириллическая
// буква в UTF-8 занимает два.
const MAX_PASSWORD_BYTES = 72;
const MAX_EMAIL = 254;

/**
 * Частота регистраций с одного адреса.
 *
 * Аккаунт создаётся мгновенно и без подтверждения почты, а лимиты генерации
 * считаются на аккаунт. Без этой проверки скрипт мог наплодить сотню
 * аккаунтов за минуту — и сотню дневных лимитов вместе с ними.
 *
 * Счётчик живёт в памяти экземпляра функции, поэтому это заслон от
 * простого скрипта, а не от распределённой атаки. Последний рубеж — общий
 * дневной потолок генераций в /api/projects: он не зависит от числа
 * аккаунтов вовсе.
 */
const SIGNUPS_PER_WINDOW = 5;
const WINDOW_MS = 60 * 60 * 1000;
const recent = new Map<string, number[]>();

function clientAddress(request: Request): string {
  // Площадка сама ставит этот заголовок; первый адрес в списке — клиент.
  const forwarded = request.headers.get("x-forwarded-for") ?? "";
  return forwarded.split(",")[0]?.trim() || request.headers.get("x-real-ip") || "unknown";
}

function throttled(address: string, now = Date.now()): boolean {
  const fresh = (recent.get(address) ?? []).filter((t) => now - t < WINDOW_MS);
  if (fresh.length >= SIGNUPS_PER_WINDOW) {
    recent.set(address, fresh);
    return true;
  }
  fresh.push(now);
  recent.set(address, fresh);
  // Память не должна расти вечно: изредка выбрасываем остывшие записи.
  if (recent.size > 5000) {
    for (const [key, times] of recent) {
      if (!times.some((t) => now - t < WINDOW_MS)) recent.delete(key);
    }
  }
  return false;
}

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

  const body = (payload ?? {}) as { email?: unknown; password?: unknown };
  const email = typeof body.email === "string" ? body.email.trim().toLowerCase() : "";
  const password = typeof body.password === "string" ? body.password : "";

  if (!email || email.length > MAX_EMAIL || !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) {
    return NextResponse.json({ error: "invalid_email" }, { status: 400 });
  }
  if (password.length < MIN_PASSWORD) {
    return NextResponse.json({ error: "weak_password" }, { status: 400 });
  }
  if (new TextEncoder().encode(password).length > MAX_PASSWORD_BYTES) {
    return NextResponse.json({ error: "password_too_long" }, { status: 400 });
  }

  // Проверка частоты — после проверки полей: опечатка в почте не должна
  // съедать попытку.
  if (throttled(clientAddress(request))) {
    return NextResponse.json({ error: "signup_throttled" }, { status: 429 });
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
    if (!taken) console.error("signup failed:", error.status, error.message);
    return NextResponse.json(
      { error: taken ? "email_taken" : "signup_failed" },
      { status: taken ? 409 : 500 }
    );
  }

  return NextResponse.json({ ok: true }, { status: 201 });
}
