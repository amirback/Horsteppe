-- Покрытие настоящим видео и честный итог сборки.
--
-- До этой миграции покрытие считалось в конвейере, писалось в лог и там же
-- умирало. Пользователь видел «Готово» одинаково и для ролика, собранного из
-- настоящих клипов, и для ролика, где ни один платный вызов не прошёл. ТЗ §32
-- запрещает такое молчание прямо: результат ниже цели — это не чистый успех.
--
-- Отдельного статуса «частично» не хватило бы: важно не только что цель не
-- взята, но и почему — кончились деньги, упал провайдер, режим был безопасный.

alter table public.projects
  add column real_video_coverage numeric(5, 4)
    check (real_video_coverage is null or real_video_coverage between 0 and 1);

-- Короткий отчёт инспектора для интерфейса: длительность, доля почти
-- статичного времени, замирания, список замечаний. Целиком, одним куском —
-- выбирать по отдельным полям его никто не будет.
alter table public.projects
  add column quality jsonb;

-- Человеческая причина: «платные вызовы отключены», «кончился бюджет»,
-- «провайдер недоступен». Показывается рядом с плеером.
alter table public.projects
  add column degraded_reason text;

-- Новый статус. Ролик готов и играется, но обещание по настоящему движению
-- не выполнено — и об этом сказано вслух, а не спрятано.
alter table public.projects
  drop constraint projects_status_check;

alter table public.projects
  add constraint projects_status_check
  check (status in ('queued', 'generating', 'done', 'done_degraded', 'failed'));

comment on column public.projects.real_video_coverage is
  'Доля таймлайна, закрытая настоящим AI-видео. Движение по фотографии сюда не входит никогда.';
comment on column public.projects.degraded_reason is
  'Почему ролик готов, но ниже цели: безопасный режим, потолок бюджета, отказ провайдера.';
