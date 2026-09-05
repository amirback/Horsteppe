-- AI Video Studio — initial schema.
-- Run in Supabase SQL Editor (or via supabase db push).

-- ============================================================
-- Tables
-- ============================================================

create table public.projects (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references auth.users (id) on delete cascade,
  topic         text not null check (char_length(topic) between 3 and 500),
  style         text not null default 'cinematic',
  duration_sec  int  not null default 30 check (duration_sec between 10 and 60),
  status        text not null default 'queued'
                check (status in ('queued', 'generating', 'done', 'failed')),
  -- Human-readable progress line for the UI, e.g. "Сцена 2/4: генерация видео"
  status_detail text,
  error_message text,
  cost_usd      numeric(10, 4) not null default 0,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

create index projects_user_id_created_at_idx on public.projects (user_id, created_at desc);

create table public.scenes (
  id                 uuid primary key default gen_random_uuid(),
  project_id         uuid not null references public.projects (id) on delete cascade,
  order_index        int  not null,
  narration          text not null,
  image_prompt       text not null,
  audio_url          text,
  audio_duration_sec numeric(8, 3),
  image_url          text,
  video_url          text,
  -- Per-scene progress allows the worker to resume without re-paying providers
  status             text not null default 'pending'
                     check (status in ('pending', 'audio_done', 'image_done', 'video_done', 'failed')),
  error_message      text,
  created_at         timestamptz not null default now(),
  unique (project_id, order_index)
);

create index scenes_project_id_idx on public.scenes (project_id);

create table public.renders (
  id              uuid primary key default gen_random_uuid(),
  project_id      uuid not null references public.projects (id) on delete cascade,
  final_video_url text not null,
  duration_sec    numeric(8, 3),
  created_at      timestamptz not null default now()
);

create index renders_project_id_idx on public.renders (project_id);

-- Job queue: one row per generation task. Worker claims rows with
-- FOR UPDATE SKIP LOCKED via claim_next_job(). Postgres is the queue —
-- no Redis needed.
create table public.jobs (
  id           bigint generated always as identity primary key,
  project_id   uuid not null unique references public.projects (id) on delete cascade,
  status       text not null default 'queued'
               check (status in ('queued', 'processing', 'done', 'failed')),
  attempts     int  not null default 0,
  max_attempts int  not null default 2,
  run_after    timestamptz not null default now(),
  locked_at    timestamptz,
  locked_by    text,
  last_error   text,
  created_at   timestamptz not null default now()
);

create index jobs_status_run_after_idx on public.jobs (status, run_after);

-- Per-call provider cost log — unit economics per generated video.
create table public.cost_events (
  id         bigint generated always as identity primary key,
  project_id uuid not null references public.projects (id) on delete cascade,
  step       text not null,   -- script | tts | image | video | render
  provider   text not null,   -- anthropic | elevenlabs | fal | ffmpeg
  detail     text,
  amount_usd numeric(10, 5) not null default 0,
  created_at timestamptz not null default now()
);

create index cost_events_project_id_idx on public.cost_events (project_id);

-- ============================================================
-- updated_at trigger
-- ============================================================

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger projects_set_updated_at
  before update on public.projects
  for each row execute function public.set_updated_at();

-- ============================================================
-- Row Level Security
-- Users can read their own data and create projects.
-- All writes during generation go through the service role
-- (API routes / worker), which bypasses RLS.
-- ============================================================

alter table public.projects    enable row level security;
alter table public.scenes      enable row level security;
alter table public.renders     enable row level security;
alter table public.jobs        enable row level security;
alter table public.cost_events enable row level security;

create policy "projects: select own"
  on public.projects for select
  using (auth.uid() = user_id);

create policy "scenes: select own"
  on public.scenes for select
  using (exists (
    select 1 from public.projects p
    where p.id = scenes.project_id and p.user_id = auth.uid()
  ));

create policy "renders: select own"
  on public.renders for select
  using (exists (
    select 1 from public.projects p
    where p.id = renders.project_id and p.user_id = auth.uid()
  ));

-- jobs / cost_events: no policies -> only service role has access.

-- ============================================================
-- Queue functions (SECURITY DEFINER, service-role only)
-- ============================================================

-- Atomically claim the next queued job. Safe for multiple workers.
create or replace function public.claim_next_job(worker_id text)
returns setof public.jobs
language sql
security definer
set search_path = public
as $$
  update public.jobs
  set status = 'processing',
      locked_at = now(),
      locked_by = worker_id,
      attempts = attempts + 1
  where id = (
    select id from public.jobs
    where status = 'queued' and run_after <= now()
    order by id
    for update skip locked
    limit 1
  )
  returning *;
$$;

-- Re-queue jobs stuck in 'processing' (worker crashed mid-run).
create or replace function public.requeue_stale_jobs(stale_minutes int default 30)
returns int
language plpgsql
security definer
set search_path = public
as $$
declare
  n int;
begin
  update public.jobs
  set status = case when attempts >= max_attempts then 'failed' else 'queued' end,
      locked_at = null,
      locked_by = null,
      last_error = coalesce(last_error, '') || ' [requeued: stale lock]'
  where status = 'processing'
    and locked_at < now() - make_interval(mins => stale_minutes);
  get diagnostics n = row_count;
  return n;
end;
$$;

revoke execute on function public.claim_next_job(text) from public, anon, authenticated;
revoke execute on function public.requeue_stale_jobs(int) from public, anon, authenticated;

-- ============================================================
-- Storage: public bucket for generated media
-- ============================================================

insert into storage.buckets (id, name, public)
values ('media', 'media', true)
on conflict (id) do nothing;

-- Uploads only via service role (worker). Public read is implied by public bucket.
