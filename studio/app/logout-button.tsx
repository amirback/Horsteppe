"use client";

import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

export function LogoutButton() {
  const router = useRouter();

  async function handleLogout() {
    await createClient().auth.signOut();
    router.push("/");
    router.refresh();
  }

  return (
    <button onClick={handleLogout} className="transition-colors hover:text-white">
      Выйти
    </button>
  );
}
