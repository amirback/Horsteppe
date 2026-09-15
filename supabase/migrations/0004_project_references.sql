-- Референс — фотография, которую принёс пользователь: снимок товара для
-- рекламы или кадр, который надо оживить. До этой миграции такого понятия не
-- было вовсе: проект описывался одной строкой темы, и товар физически не мог
-- попасть в генерацию. Отсюда и главная претензия к результату — ролик не
-- про твой товар, а про похожий, придуманный моделью.
--
-- Референс принадлежит проекту, а не кадру: одна и та же фотография нужна
-- нескольким кадрам сразу (герой, деталь, финальная заставка). Связь
-- «кадр → референс» живёт в shots.first_frame_reference, колонка для неё
-- заведена ещё в 0003_shots.sql и до сих пор пустовала.
--
-- Файл лежит там же, где остальные ассеты проекта:
-- media/projects/<project_id>/references/<n>.<ext> — изоляция по проекту уже
-- обеспечена схемой путей в db.upload().

create table public.project_references (
  id           uuid primary key default gen_random_uuid(),
  project_id   uuid not null references public.projects (id) on delete cascade,
  order_index  int  not null,

  -- Главный референс: с него начинается режим «фото → видео», и он же
  -- считается каноническим видом товара, когда снимков несколько.
  is_primary   boolean not null default false,

  -- Ракурс. Автоматическую классификацию ТЗ прямо просит не переусложнять на
  -- первой волне, поэтому значение ставит человек или остаётся 'unknown'.
  view_type    text not null default 'unknown'
               check (view_type in ('front', 'side', 'detail', 'packaging', 'lifestyle', 'unknown')),

  storage_path text not null,
  -- Именно этот URL уходит провайдеру image-to-video, поэтому он обязан быть
  -- публично достижимым, а не подписанным на час.
  public_url   text not null,

  mime_type    text not null,
  width        int,
  height       int,
  bytes        int,

  created_at   timestamptz not null default now(),
  unique (project_id, order_index)
);

create index project_references_project_id_idx
  on public.project_references (project_id, order_index);

-- Главный референс в проекте ровно один. Частичный индекс дешевле триггера и
-- не даёт коду «на всякий случай» пометить главными сразу двоих.
create unique index project_references_primary_idx
  on public.project_references (project_id)
  where is_primary;

alter table public.project_references enable row level security;

-- Та же форма политики, что у scenes, shots и renders: читает владелец
-- проекта, пишет служебная роль, то есть воркер и серверный маршрут загрузки.
create policy "project_references: select own"
  on public.project_references for select
  using (exists (
    select 1 from public.projects p
    where p.id = project_references.project_id and p.user_id = auth.uid()
  ));

-- ------------------------------------------------------------------ проект --

-- Тип проекта решает, какую режиссуру включать: общую историю, рекламу товара
-- или оживление одной фотографии. Значение по умолчанию сохраняет поведение
-- всех уже собранных проектов.
alter table public.projects
  add column project_type text not null default 'general_video'
    check (project_type in ('general_video', 'product_ad', 'image_to_video'));

-- Бриф товара: название, описание, выгоды, аудитория, цель, призыв к
-- действию. Одним jsonb, а не семью колонками, намеренно: эти поля читаются
-- только целиком и только режиссёром, ни одно из них не участвует в выборках.
-- Проверка формы живёт в коде, где её видно тестом.
alter table public.projects
  add column brief jsonb not null default '{}'::jsonb;

-- Потолок расходов на проект. NULL — потолка нет (поведение до этой
-- миграции). Сам по себе столбец ничего не запрещает: запрет делает
-- BudgetGuard в воркере, здесь только объявленная пользователем сумма.
alter table public.projects
  add column max_budget_usd numeric(10, 4)
    check (max_budget_usd is null or max_budget_usd >= 0);

comment on table public.project_references is
  'Фотографии пользователя: снимки товара для рекламы или кадр для оживления. Источник для image-to-video.';
comment on column public.project_references.public_url is
  'Публичный URL — его получает провайдер image-to-video. Подписанная ссылка не подходит: генерация идёт минутами.';
comment on column public.projects.project_type is
  'general_video — тема → ролик; product_ad — фото товара → реклама; image_to_video — фото → настоящее движение.';
comment on column public.projects.brief is
  'Бриф товара целиком: product_name, product_description, product_benefits[], target_audience, ad_goal, call_to_action, product_url.';
