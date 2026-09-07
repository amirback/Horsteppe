import { createClient as createSupabaseClient } from "@supabase/supabase-js";

/**
 * Служебный клиент: обходит политики доступа. Только на сервере.
 * Нужен для записей, которые пользователю делать нельзя, — постановка в очередь.
 */
export function createAdminClient() {
  return createSupabaseClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { persistSession: false, autoRefreshToken: false } }
  );
}
