import Link from "next/link";
import { createClient } from "@/lib/supabase/server";

const STATUS_STYLES: Record<string, { label: string; cls: string }> = {
  queued: { label: "В очереди", cls: "border-white/10 bg-white/5 text-neutral-400" },
  generating: { label: "Генерируется", cls: "border-amber-500/30 bg-amber-500/10 text-amber-400" },
  done: { label: "Готово", cls: "border-emerald-500/30 bg-emerald-500/10 text-emerald-400" },
  failed: { label: "Ошибка", cls: "border-red-500/30 bg-red-500/10 text-red-400" },
};

export default async function ProjectsPage() {
  const supabase = await createClient();
  const { data: projects } = await supabase
    .from("projects")
    .select("id, topic, status, status_detail, created_at")
    .order("created_at", { ascending: false })
    .limit(50);

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Мои видео</h1>
          <p className="mt-1 text-sm text-neutral-400">{projects?.length ?? 0} всего</p>
        </div>
        <Link href="/" className="btn-primary max-sm:w-full">
          + Новое видео
        </Link>
      </div>

      {!projects?.length ? (
        <div className="card flex flex-col items-center gap-3 px-8 py-20 text-center">
          <p className="text-neutral-400">Пока нет видео</p>
          <Link href="/" className="btn-secondary mt-2">
            Создать первое
          </Link>
        </div>
      ) : (
        <ul className="card divide-y divide-white/10 overflow-hidden">
          {projects.map((p) => {
            const s = STATUS_STYLES[p.status] ?? STATUS_STYLES.queued;
            return (
              <li key={p.id}>
                <Link
                  href={`/projects/${p.id}`}
                  className="flex items-center justify-between gap-3 px-4 py-4 transition-colors hover:bg-white/[0.05] sm:px-6"
                >
                  <span className="line-clamp-1 text-sm font-medium text-neutral-200">
                    {p.topic}
                  </span>
                  <span
                    className={`shrink-0 rounded-full border px-3 py-1 text-xs font-medium ${s.cls}`}
                  >
                    {s.label}
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
