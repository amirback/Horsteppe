import { createBrowserClient } from "@supabase/ssr";

/** Клиент для браузера — используется только на странице входа. */
export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );
}
