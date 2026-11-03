-- Horsteppe V1: надёжность платной генерации и оценка результата.
-- Вставить целиком в Supabase → SQL Editor → Run. Повторный запуск безопасен:
-- каждая команда проверяет, не сделана ли она уже.
--
-- Сайт и сборщик работают и до применения этой миграции — новые поля они
-- пишут только тогда, когда те существуют.

-- ============================================================
-- 1. Номер задачи у провайдера видео
-- ============================================================
-- Higgsfield принимает задачу и отдаёт результат через минуты. До этой
-- миграции номер задачи жил только в памяти сборщика: упал процесс или
-- закрыли окно — номер пропал, и при повторе клип заказывался заново.
-- Оплачиваются обе задачи: их спецификация прямо говорит, что записи об
-- оплате переживают даже удаление задачи.
--
-- Номер записывается в тот миг, когда провайдер принял задачу. Повтор
-- проекта сначала спрашивает о ней провайдера и забирает готовый клип, а не
-- платит второй раз.

alter table public.shots
  add column if not exists provider_request_id   text,
  add column if not exists provider_status       text,
  add column if not exists provider_status_url   text,
  add column if not exists provider_submitted_at timestamptz;

create index if not exists shots_provider_request_idx
  on public.shots (provider_request_id)
  where provider_request_id is not null;

comment on column public.shots.provider_request_id is
  'Номер задачи у провайдера видео. Пока он есть, а клипа нет, повтор забирает результат этой задачи вместо нового заказа.';
comment on column public.shots.provider_status is
  'Последнее известное состояние задачи у провайдера: queued, in_progress, completed, failed, canceled, nsfw — или наша пометка о сбое связи.';

-- ============================================================
-- 2. Зависшая задача не оставляет проект «в работе» навсегда
-- ============================================================
-- Если сборщик умер посреди проекта, задача через 30 минут возвращается в
-- очередь. Но когда попытки кончались, задача становилась failed, а проект
-- оставался generating — навсегда. Человек видел вечную «сборку», кнопки
-- повтора не было (она есть только у упавших проектов), а лимит «один
-- проект одновременно» не давал создать новый. Тупик без выхода.
--
-- Тексты совпадают со строками сборщика: сайт переводит их на en и kk.

create or replace function public.requeue_stale_jobs(stale_minutes int default 30)
returns int
language plpgsql
security definer
set search_path = public
as $$
declare
  n int;
begin
  with stale as (
    update public.jobs
    set status = case when attempts >= max_attempts then 'failed' else 'queued' end,
        locked_at = null,
        locked_by = null,
        last_error = coalesce(last_error, '') || ' [requeued: stale lock]'
    where status = 'processing'
      and locked_at < now() - make_interval(mins => stale_minutes)
    returning project_id, status
  ),
  exhausted as (
    update public.projects p
    set status = 'failed',
        status_detail = null,
        error_message = 'Не удалось сгенерировать видео. Попробуйте ещё раз позже.'
    from stale s
    where s.project_id = p.id
      and s.status = 'failed'
      and p.status in ('queued', 'generating')
    returning p.id
  ),
  retried as (
    update public.projects p
    set status_detail = 'Повторная попытка…'
    from stale s
    where s.project_id = p.id
      and s.status = 'queued'
      and p.status in ('queued', 'generating')
    returning p.id
  )
  select count(*) into n from stale;
  return n;
end;
$$;

revoke execute on function public.requeue_stale_jobs(int) from public, anon, authenticated;

-- ============================================================
-- 3. Оценка результата
-- ============================================================
-- «Хороший результат» или «нужно улучшить», а при втором — причины и
-- необязательный комментарий. Оценка привязана к конкретной генерации
-- (render_id) и хранит снимок того, чем она сделана: модели, провайдеры,
-- настройки. Это сбор данных для будущего выбора моделей, а не обучение.
--
-- Пишет только сервер сайта (служебная роль) после проверки, что проект
-- принадлежит этому человеку. Читать человек может только свои оценки.

create table if not exists public.project_feedback (
  id          bigint generated always as identity primary key,
  project_id  uuid not null references public.projects (id) on delete cascade,
  user_id     uuid not null references auth.users (id) on delete cascade,
  render_id   uuid references public.renders (id) on delete set null,
  rating      text not null check (rating in ('good', 'needs_improvement')),
  reasons     text[] not null default '{}'
              check (reasons <@ array['off_prompt', 'visuals', 'motion', 'sound',
                                      'text', 'length', 'other']::text[]),
  comment     text check (comment is null or char_length(comment) <= 1000),
  context     jsonb not null default '{}'::jsonb,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  unique (project_id, user_id)
);

create index if not exists project_feedback_rating_idx
  on public.project_feedback (rating, created_at desc);

alter table public.project_feedback enable row level security;

drop policy if exists "project_feedback: select own" on public.project_feedback;
create policy "project_feedback: select own"
  on public.project_feedback for select
  using (auth.uid() = user_id);

drop trigger if exists project_feedback_set_updated_at on public.project_feedback;
create trigger project_feedback_set_updated_at
  before update on public.project_feedback
  for each row execute function public.set_updated_at();

comment on table public.project_feedback is
  'Оценка готового ролика человеком: good / needs_improvement, причины, комментарий и снимок настроек генерации.';
comment on column public.project_feedback.context is
  'Снимок генерации на момент оценки: модели и провайдеры клипов, формат, длительность, покрытие настоящим видео. Собирается сервером, клиенту не доверяется.';
