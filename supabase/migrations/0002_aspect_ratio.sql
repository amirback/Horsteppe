-- Формат кадра на уровне проекта. Раньше он был зашит в код воркера
-- как 1080x1920; теперь выбирается пользователем при создании проекта.

alter table public.projects
  add column if not exists aspect_ratio text not null default '9:16'
    check (aspect_ratio in ('9:16', '16:9', '1:1', '4:5'));

comment on column public.projects.aspect_ratio is
  'Формат кадра: 9:16 для Shorts/Reels/TikTok, 16:9 для YouTube, 1:1 и 4:5 для лент.';
