-- 0007: пакеты, заказы и кредиты на ролики.
--
-- Путь человека: выбрал пакет → оплатил → получил кредиты → описал идею →
-- ролик собран → кредит списан. Один кредит — одна успешная генерация.
--
-- Правила, которые держит сама база, а не код сайта:
--   * кредиты зачисляются только по оплаченному заказу и ровно один раз;
--   * баланс не уходит в минус (check), два одновременных заказа ролика не
--     тратят один кредит дважды (атомарный update);
--   * пока ролик собирается, кредит в резерве; «Готово» — списан; ошибка или
--     ролик с оговоркой — вернулся. Это делает триггер на смене статуса
--     проекта, поэтому сборщик (воркер) ничего не знает о кредитах;
--   * каждое движение кредита — строка в журнале.
--
-- Миграция только добавляет. Сайт до неё работает по-старому: без кредитов.
-- Повторный запуск безопасен.

-- ============================================================
-- Пакеты
-- ============================================================

create table if not exists public.packages (
  id          text primary key,                       -- код из КП: E1 … P5
  tier        text not null check (tier in ('economy', 'medium', 'premium')),
  videos      int  not null check (videos between 1 and 1000),
  video_sec   int  not null check (video_sec between 10 and 60),
  price_kzt   int  not null check (price_kzt > 0),
  -- Пакет виден покупателям только после включения основателем.
  active      boolean not null default false,
  sort_order  int  not null default 0,
  source      text,                                   -- откуда цена
  updated_at  timestamptz not null default now()
);

comment on table public.packages is
  'Пакеты роликов. Цены не выдумываются: значения из КП основателя, включает и правит их основатель.';

-- Значения из коммерческого предложения от 09.11.2026. Выключены: цены КП
-- включают ручную работу, а цена самостоятельной генерации от 14.11.2026
-- ниже (docs/MONEY.md §8.1). Какие цены продавать — решение основателя.
insert into public.packages (id, tier, videos, video_sec, price_kzt, sort_order, source) values
  ('E1', 'economy',  5, 15,  11000, 11, 'КП 09.11.2026'),
  ('E2', 'economy', 10, 15,  22100, 12, 'КП 09.11.2026'),
  ('E3', 'economy', 20, 15,  44100, 13, 'КП 09.11.2026'),
  ('E4', 'economy', 30, 15,  66200, 14, 'КП 09.11.2026'),
  ('E5', 'economy', 30, 30,  78800, 15, 'КП 09.11.2026'),
  ('M1', 'medium',   5, 15,  12100, 21, 'КП 09.11.2026'),
  ('M2', 'medium',  10, 15,  24200, 22, 'КП 09.11.2026'),
  ('M3', 'medium',  20, 15,  48300, 23, 'КП 09.11.2026'),
  ('M4', 'medium',  30, 15,  72500, 24, 'КП 09.11.2026'),
  ('M5', 'medium',  30, 30,  94500, 25, 'КП 09.11.2026'),
  ('P1', 'premium',  5, 15,  16300, 31, 'КП 09.11.2026'),
  ('P2', 'premium', 10, 15,  32600, 32, 'КП 09.11.2026'),
  ('P3', 'premium', 20, 15,  65100, 33, 'КП 09.11.2026'),
  ('P4', 'premium', 30, 15,  97700, 34, 'КП 09.11.2026'),
  ('P5', 'premium', 30, 30, 170100, 35, 'КП 09.11.2026')
on conflict (id) do nothing;

-- ============================================================
-- Заказы
-- ============================================================

create table if not exists public.orders (
  id                  uuid primary key default gen_random_uuid(),
  user_id             uuid not null references auth.users (id) on delete cascade,
  -- Почта покупателя: по ней основатель сверяет ручную оплату.
  email               text,
  package_id          text not null references public.packages (id),
  -- Снимок пакета на момент заказа: правка пакета не меняет чужие заказы.
  tier                text not null check (tier in ('economy', 'medium', 'premium')),
  videos              int  not null check (videos > 0),
  video_sec           int  not null check (video_sec between 10 and 60),
  amount_kzt          int  not null check (amount_kzt > 0),
  status              text not null default 'pending'
                      check (status in ('pending', 'paid', 'canceled')),
  provider            text not null default 'manual',
  provider_payment_id text,
  paid_at             timestamptz,
  confirmed_by        text,
  created_at          timestamptz not null default now(),
  unique (provider, provider_payment_id)
);

create index if not exists orders_user_created_idx on public.orders (user_id, created_at desc);
create index if not exists orders_status_idx on public.orders (status, created_at desc);

-- ============================================================
-- Кредиты
-- ============================================================

-- Кредит привязан к уровню качества и длине ролика: «Premium, до 30 с».
create table if not exists public.credit_balances (
  user_id    uuid not null references auth.users (id) on delete cascade,
  tier       text not null check (tier in ('economy', 'medium', 'premium')),
  video_sec  int  not null check (video_sec between 10 and 60),
  available  int  not null default 0 check (available >= 0),
  reserved   int  not null default 0 check (reserved >= 0),
  updated_at timestamptz not null default now(),
  primary key (user_id, tier, video_sec)
);

-- Резерв по проекту. Без внешнего ключа на projects: удаление проекта
-- возвращает кредит триггером ниже, а не теряет его вместе со строкой.
create table if not exists public.credit_reservations (
  project_id uuid primary key,
  user_id    uuid not null references auth.users (id) on delete cascade,
  tier       text not null,
  video_sec  int  not null,
  state      text not null default 'reserved' check (state in ('reserved', 'spent', 'released')),
  created_at timestamptz not null default now(),
  settled_at timestamptz
);

create table if not exists public.credit_ledger (
  id              bigint generated always as identity primary key,
  user_id         uuid not null references auth.users (id) on delete cascade,
  tier            text not null,
  video_sec       int  not null,
  delta_available int  not null,
  delta_reserved  int  not null,
  kind            text not null check (kind in ('purchase', 'reserve', 'spend', 'release')),
  order_id        uuid references public.orders (id),
  project_id      uuid,
  note            text,
  created_at      timestamptz not null default now()
);

create index if not exists credit_ledger_user_created_idx on public.credit_ledger (user_id, created_at desc);
-- Второй барьер идемпотентности: заказ зачисляется ровно один раз.
create unique index if not exists credit_ledger_one_purchase_per_order
  on public.credit_ledger (order_id) where kind = 'purchase';

-- Уровень качества проекта — потолок моделей для сборщика:
-- economy — только лёгкий уровень, medium — не выше среднего, premium — все.
-- Пусто — проект без кредитов (до этой миграции): как раньше, без потолка.
alter table public.projects
  add column if not exists quality_tier text
  check (quality_tier in ('economy', 'medium', 'premium'));

-- ============================================================
-- Доступ
-- ============================================================

alter table public.packages            enable row level security;
alter table public.orders              enable row level security;
alter table public.credit_balances     enable row level security;
alter table public.credit_reservations enable row level security;
alter table public.credit_ledger       enable row level security;

-- Пишет только служебная роль (API сайта). Читать — своё.
drop policy if exists "packages: select active" on public.packages;
create policy "packages: select active" on public.packages for select using (active);

drop policy if exists "orders: select own" on public.orders;
create policy "orders: select own" on public.orders for select using (auth.uid() = user_id);

drop policy if exists "credit_balances: select own" on public.credit_balances;
create policy "credit_balances: select own" on public.credit_balances for select using (auth.uid() = user_id);

drop policy if exists "credit_reservations: select own" on public.credit_reservations;
create policy "credit_reservations: select own" on public.credit_reservations for select using (auth.uid() = user_id);

drop policy if exists "credit_ledger: select own" on public.credit_ledger;
create policy "credit_ledger: select own" on public.credit_ledger for select using (auth.uid() = user_id);

-- ============================================================
-- Зачисление оплаченного заказа
-- ============================================================

-- Идемпотентно: второй вызов по тому же заказу ничего не зачисляет и
-- возвращает 'already_paid'. Сумма сверяется, если её сообщил провайдер.
create or replace function public.grant_order_credits(
  p_order uuid, p_provider text, p_payment_id text, p_amount_kzt int, p_confirmed_by text
) returns text
language plpgsql
security definer
set search_path = public
as $$
declare
  o public.orders;
begin
  select * into o from public.orders where id = p_order for update;
  if not found then
    raise exception 'order_not_found';
  end if;
  if o.status = 'paid' then
    return 'already_paid';
  end if;
  if p_amount_kzt is not null and p_amount_kzt <> o.amount_kzt then
    raise exception 'amount_mismatch';
  end if;

  -- Отменённый заказ тоже зачисляется: если деньги пришли, кредиты должны.
  update public.orders
     set status = 'paid', paid_at = now(),
         provider = coalesce(p_provider, provider),
         provider_payment_id = coalesce(p_payment_id, provider_payment_id),
         confirmed_by = p_confirmed_by
   where id = o.id;

  insert into public.credit_balances (user_id, tier, video_sec, available)
  values (o.user_id, o.tier, o.video_sec, o.videos)
  on conflict (user_id, tier, video_sec)
  do update set available = public.credit_balances.available + excluded.available, updated_at = now();

  insert into public.credit_ledger (user_id, tier, video_sec, delta_available, delta_reserved, kind, order_id, note)
  values (o.user_id, o.tier, o.video_sec, o.videos, 0, 'purchase', o.id, p_confirmed_by);
  return 'paid';
end;
$$;

-- ============================================================
-- Резерв кредита под проект
-- ============================================================

-- Берёт самый короткий подходящий кредит уровня: на ролик 15 с не тратится
-- кредит на 30 с, если есть на 15. Повторный вызов по проекту с живым или
-- списанным резервом ничего не берёт. Нет кредита — исключение no_credits.
create or replace function public.reserve_credit(p_project uuid, p_tier text)
returns table (tier text, video_sec int)
language plpgsql
security definer
set search_path = public
as $$
#variable_conflict use_column
declare
  p public.projects;
  b public.credit_balances;
  held public.credit_reservations;
begin
  select * into p from public.projects where id = p_project;
  if not found then
    raise exception 'project_not_found';
  end if;

  select * into held from public.credit_reservations r where r.project_id = p_project for update;
  if found and held.state in ('reserved', 'spent') then
    return query select held.tier, held.video_sec;
    return;
  end if;

  update public.credit_balances cb
     set available = cb.available - 1, reserved = cb.reserved + 1, updated_at = now()
   where cb.user_id = p.user_id
     and cb.tier = p_tier
     and cb.available > 0
     and cb.video_sec = (
       select min(x.video_sec) from public.credit_balances x
        where x.user_id = p.user_id and x.tier = p_tier
          and x.video_sec >= p.duration_sec and x.available > 0)
  returning cb.* into b;
  if not found then
    raise exception 'no_credits';
  end if;

  insert into public.credit_reservations (project_id, user_id, tier, video_sec, state)
  values (p_project, p.user_id, b.tier, b.video_sec, 'reserved')
  on conflict (project_id) do update
    set tier = excluded.tier, video_sec = excluded.video_sec, state = 'reserved',
        created_at = now(), settled_at = null;

  insert into public.credit_ledger (user_id, tier, video_sec, delta_available, delta_reserved, kind, project_id)
  values (p.user_id, b.tier, b.video_sec, -1, 1, 'reserve', p_project);

  return query select b.tier, b.video_sec;
end;
$$;

-- ============================================================
-- Расчёт по итогу проекта
-- ============================================================

-- Списать ('spend') или вернуть ('release') живой резерв проекта. Без живого
-- резерва ничего не делает и возвращает false: повторный «Готово» второй раз
-- не спишет, повторная ошибка второй раз не вернёт.
create or replace function public.settle_credit(p_project uuid, p_outcome text)
returns boolean
language plpgsql
security definer
set search_path = public
as $$
declare
  r public.credit_reservations;
begin
  if p_outcome not in ('spend', 'release') then
    raise exception 'bad_outcome';
  end if;
  select * into r from public.credit_reservations
   where project_id = p_project and state = 'reserved' for update;
  if not found then
    return false;
  end if;

  if p_outcome = 'spend' then
    update public.credit_balances
       set reserved = reserved - 1, updated_at = now()
     where user_id = r.user_id and tier = r.tier and video_sec = r.video_sec;
    update public.credit_reservations set state = 'spent', settled_at = now() where project_id = p_project;
    insert into public.credit_ledger (user_id, tier, video_sec, delta_available, delta_reserved, kind, project_id)
    values (r.user_id, r.tier, r.video_sec, 0, -1, 'spend', p_project);
  else
    update public.credit_balances
       set reserved = reserved - 1, available = available + 1, updated_at = now()
     where user_id = r.user_id and tier = r.tier and video_sec = r.video_sec;
    update public.credit_reservations set state = 'released', settled_at = now() where project_id = p_project;
    insert into public.credit_ledger (user_id, tier, video_sec, delta_available, delta_reserved, kind, project_id)
    values (r.user_id, r.tier, r.video_sec, 1, -1, 'release', p_project);
  end if;
  return true;
end;
$$;

-- «Готово» — кредит списан. «Ошибка» и «готово с оговоркой» (обещанное
-- настоящее движение не выполнено) — кредит вернулся. Удаление проекта с
-- живым резервом — тоже возврат.
create or replace function public.settle_project_credit()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if tg_op = 'DELETE' then
    perform public.settle_credit(old.id, 'release');
    return old;
  end if;
  if new.status is distinct from old.status then
    if new.status = 'done' then
      perform public.settle_credit(new.id, 'spend');
    elsif new.status in ('failed', 'done_degraded') then
      perform public.settle_credit(new.id, 'release');
    end if;
  end if;
  return new;
end;
$$;

drop trigger if exists projects_settle_credit on public.projects;
create trigger projects_settle_credit
  after update of status on public.projects
  for each row execute function public.settle_project_credit();

drop trigger if exists projects_release_credit_on_delete on public.projects;
create trigger projects_release_credit_on_delete
  after delete on public.projects
  for each row execute function public.settle_project_credit();

revoke execute on function public.grant_order_credits(uuid, text, text, int, text) from public, anon, authenticated;
revoke execute on function public.reserve_credit(uuid, text) from public, anon, authenticated;
revoke execute on function public.settle_credit(uuid, text) from public, anon, authenticated;
revoke execute on function public.settle_project_credit() from public, anon, authenticated;
grant execute on function public.grant_order_credits(uuid, text, text, int, text) to service_role;
grant execute on function public.reserve_credit(uuid, text) to service_role;
grant execute on function public.settle_credit(uuid, text) to service_role;
