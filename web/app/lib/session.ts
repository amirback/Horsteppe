import { createClient } from "@/lib/supabase/server";
import { isBackendReady } from "@/lib/supabase/env";

/**
 * Почта вошедшего пользователя или null.
 *
 * Никогда не бросает исключение: страницы должны открываться и без базы,
 * иначе неподключённый backend положит весь сайт, включая лендинг.
 */
export async function getSessionEmail(): Promise<string | null> {
  if (!isBackendReady()) return null;
  try {
    const supabase = await createClient();
    const {
      data: { user },
    } = await supabase.auth.getUser();
    return user?.email ?? null;
  } catch {
    return null;
  }
}
