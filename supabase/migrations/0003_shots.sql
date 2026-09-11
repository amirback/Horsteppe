-- Кадр (shot) — единица монтажа. До этой миграции единицей была сцена, и
-- ровно поэтому готовый ролик выглядел слайдшоу: одна сцена = одна картинка,
-- растянутая медленным зумом на 6-7 секунд. Замер на проекте «2 students
-- businessmen»: 4 кадра по 6.7 с, 51% времени движение слабее лёгкого зума.
--
-- Сцена остаётся смысловой частью истории и владеет озвучкой; кадр — это
-- конкретный кадр камеры внутри сцены со своим планом, движением и ассетом.
--
-- Поля повторяют модель Shot из продуктового брифа Finish Mode. Того, что уже
-- живёт в scenes (narration, audio_url, audio_duration_sec), здесь намеренно
-- нет: дублировать источник истины по длительности нельзя.

create table public.shots (
  id                  uuid primary key default gen_random_uuid(),
  project_id          uuid not null references public.projects (id) on delete cascade,
  scene_id            uuid not null references public.scenes (id) on delete cascade,
  order_index         int  not null,

  -- Роль кадра в истории: hook, establishing, detail, climax, ending и т.п.
  purpose             text,
  shot_type           text,

  -- Место кадра в финальном таймлайне.
  timeline_start      numeric(8, 3),
  timeline_end        numeric(8, 3),
  -- Длительность в монтаже и длительность, которую заказали у провайдера, —
  -- разные величины: провайдер отдаёт клип 5 с, в монтаж уходит 3.2 с.
  timeline_duration   numeric(8, 3),
  generation_duration numeric(8, 3),

  visual_prompt       text not null,
  video_prompt        text,

  camera_motion       text,
  subject_motion      text,
  -- Насколько кадру нужно настоящее движение: от этого зависит, дать ли ему
  -- платное видео или обойтись движением по картинке.
  motion_requirement  text not null default 'normal'
                      check (motion_requirement in ('none', 'low', 'normal', 'high', 'critical')),

  -- Важность решает, куда уходит дорогая генерация: бюджет делится не поровну.
  visual_importance    numeric(4, 3) not null default 0.5
                       check (visual_importance between 0 and 1),
  narrative_importance numeric(4, 3) not null default 0.5
                       check (narrative_importance between 0 and 1),
  -- Кадры одной группы обязаны выглядеть одним миром: тот же герой, свет, место.
  continuity_group     text,

  -- Чем в итоге закрыт кадр. Ken Burns настоящим движением НЕ считается:
  -- на этом различении стоит метрика real_video_coverage.
  generation_mode     text not null default 'image_motion'
                      check (generation_mode in ('real_video', 'image_motion', 'static')),
  provider            text,
  model               text,

  first_frame_reference text,
  last_frame_reference  text,

  image_url           text,
  video_url           text,

  estimated_cost_usd  numeric(10, 4) not null default 0,
  actual_cost_usd     numeric(10, 4) not null default 0,

  quality_score       numeric(5, 2),
  motion_score        numeric(5, 2),
  continuity_score    numeric(5, 2),

  retry_count         int  not null default 0,
  status              text not null default 'planned'
                      check (status in ('planned', 'image_done', 'video_done', 'ready', 'failed')),
  failure_reason      text,

  created_at          timestamptz not null default now(),
  unique (project_id, order_index)
);

create index shots_project_id_idx on public.shots (project_id, order_index);
create index shots_scene_id_idx   on public.shots (scene_id);

alter table public.shots enable row level security;

-- Читать кадры может только владелец проекта — та же форма политики, что у
-- scenes и renders. Пишет только служебная роль, то есть воркер.
create policy "shots: select own"
  on public.shots for select
  using (exists (
    select 1 from public.projects p
    where p.id = shots.project_id and p.user_id = auth.uid()
  ));

comment on table public.shots is
  'Кадр камеры — единица монтажа. Сцена владеет озвучкой, кадр — картинкой и движением.';
comment on column public.shots.generation_mode is
  'real_video — настоящее AI-видео; image_motion — картинка, которую двигает FFmpeg; static — без движения. Только real_video засчитывается в real_video_coverage.';
comment on column public.shots.generation_duration is
  'Сколько секунд заказано у провайдера. В монтаж может уйти меньше — см. timeline_duration.';
