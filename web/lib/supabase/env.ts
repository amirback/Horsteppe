/**
 * Backend может быть ещё не подключён: ключей Supabase нет до тех пор, пока
 * основатель не создаст проект и не заполнит переменные окружения.
 *
 * Поэтому весь код, который ходит в базу, сначала спрашивает `isBackendReady()`.
 * Без этой проверки middleware падал бы на каждом запросе и клал весь сайт —
 * включая лендинг, который работать обязан.
 */
export function isBackendReady(): boolean {
  return Boolean(
    process.env.NEXT_PUBLIC_SUPABASE_URL && process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
  );
}

export function isAdminReady(): boolean {
  return isBackendReady() && Boolean(process.env.SUPABASE_SERVICE_ROLE_KEY);
}

export const BACKEND_OFFLINE_MESSAGE =
  "Генерация ещё не подключена: администратор не настроил доступ к базе.";
