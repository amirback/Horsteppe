// Проверка миграции 0007 на настоящем Postgres (PGlite): все миграции по
// порядку, затем сценарии денег. Боевая база не трогается.
//
// PGlite не входит в зависимости проекта — ставится во временную папку:
//   mkdir /tmp/pg && cd /tmp/pg && npm i @electric-sql/pglite
//   cp <репозиторий>/supabase/tests/credits_test.mjs .
//   node credits_test.mjs <репозиторий>/supabase/migrations
// Последняя строка вывода: «all passed» или число провалов.
import { PGlite } from "@electric-sql/pglite";
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

const dir = process.argv[2];
const db = new PGlite();
let failures = 0;
const ok = (cond, label) => {
  console.log(`${cond ? "ok  " : "FAIL"} ${label}`);
  if (!cond) failures += 1;
};
const one = async (sql, params = []) => (await db.query(sql, params)).rows[0];
const fails = async (sql, params, pattern) => {
  try {
    await db.query(sql, params);
    return false;
  } catch (e) {
    return pattern.test(e.message);
  }
};

await db.exec(`
  create role anon; create role authenticated; create role service_role;
  create schema auth;
  create table auth.users (id uuid primary key, email text);
  create function auth.uid() returns uuid language sql stable as
    $$ select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid $$;
  create schema storage;
  create table storage.buckets (id text primary key, name text, public boolean,
    file_size_limit bigint, allowed_mime_types text[]);
  grant usage on schema public to anon, authenticated;
`);

for (const file of readdirSync(dir).filter((f) => f.endsWith(".sql")).sort()) {
  await db.exec(readFileSync(join(dir, file), "utf8"));
  console.log("applied", file);
}
// Повторный запуск 0007 безопасен.
await db.exec(readFileSync(join(dir, "0007_credits.sql"), "utf8"));
ok(true, "0007 runs twice");

const U1 = "11111111-1111-1111-1111-111111111111";
const U2 = "22222222-2222-2222-2222-222222222222";
await db.exec(`insert into auth.users values ('${U1}', 'a@x'), ('${U2}', 'b@x');`);

const pk = await one("select count(*)::int n, count(*) filter (where active)::int on_ from public.packages");
ok(pk.n === 15 && pk.on_ === 0, "15 packages from the KP, all switched off");

const order = async (user, pkg) =>
  (await one(
    `insert into public.orders (user_id, package_id, tier, videos, video_sec, amount_kzt)
     select $1, id, tier, videos, video_sec, price_kzt from public.packages where id = $2 returning id`,
    [user, pkg],
  )).id;
const balance = async (user, tier, sec) =>
  (await one(
    "select available, reserved from public.credit_balances where user_id = $1 and tier = $2 and video_sec = $3",
    [user, tier, sec],
  )) ?? { available: 0, reserved: 0 };
const grant = (id, amount = null) =>
  one("select public.grant_order_credits($1, 'manual', null, $2, 'admin@test') as r", [id, amount]);

// --- зачисление ------------------------------------------------------------
const o1 = await order(U1, "P2");
ok((await grant(o1)).r === "paid", "paid order grants credits");
let b = await balance(U1, "premium", 15);
ok(b.available === 10 && b.reserved === 0, "P2 gives 10 premium credits up to 15 s");
ok((await grant(o1)).r === "already_paid", "second confirmation is a no-op");
b = await balance(U1, "premium", 15);
ok(b.available === 10, "no double credit");
const purchases = await one("select count(*)::int n from public.credit_ledger where order_id = $1", [o1]);
ok(purchases.n === 1, "one purchase line in the ledger");

const o2 = await order(U1, "E1");
ok(await fails("select public.grant_order_credits($1, 'kaspi', 'x1', 999, 'webhook')", [o2], /amount_mismatch/),
  "wrong amount from a provider is refused");
ok((await one("select status from public.orders where id = $1", [o2])).status === "pending",
  "refused order stays pending");

// --- резерв и расчёт -------------------------------------------------------
const project = async (user, sec) =>
  (await one(
    `insert into public.projects (user_id, topic, duration_sec, quality_tier)
     values ($1, 'Степь на рассвете', $2, 'premium') returning id`,
    [user, sec],
  )).id;
const reserve = (id, tier = "premium") => one("select * from public.reserve_credit($1, $2)", [id, tier]);
const state = async (id) =>
  (await one("select state from public.credit_reservations where project_id = $1", [id]))?.state;
const setStatus = (id, status) => db.query("update public.projects set status = $2 where id = $1", [id, status]);

const p1 = await project(U1, 15);
const r1 = await reserve(p1);
ok(r1.tier === "premium" && r1.video_sec === 15, "reserve picks premium 15 s");
b = await balance(U1, "premium", 15);
ok(b.available === 9 && b.reserved === 1, "one credit held while the video is made");
await reserve(p1);
b = await balance(U1, "premium", 15);
ok(b.available === 9 && b.reserved === 1, "second reserve for the same project takes nothing");

await setStatus(p1, "generating");
ok((await balance(U1, "premium", 15)).reserved === 1, "generating keeps the hold");
await setStatus(p1, "done");
b = await balance(U1, "premium", 15);
ok(b.available === 9 && b.reserved === 0 && (await state(p1)) === "spent", "done spends the credit");
await setStatus(p1, "generating");
await setStatus(p1, "done");
ok((await balance(U1, "premium", 15)).available === 9, "a second done does not spend again");

const p2 = await project(U1, 15);
await reserve(p2);
await setStatus(p2, "failed");
b = await balance(U1, "premium", 15);
ok(b.available === 9 && b.reserved === 0 && (await state(p2)) === "released", "failure returns the credit");
await setStatus(p2, "queued");
await reserve(p2);
ok((await balance(U1, "premium", 15)).available === 8, "retry holds a credit again");
await setStatus(p2, "done_degraded");
ok((await balance(U1, "premium", 15)).available === 9, "video with a caveat is not charged");

const p3 = await project(U1, 30);
ok(await fails("select * from public.reserve_credit($1, 'premium')", [p3], /no_credits/),
  "15 s credits do not pay for a 30 s video");
ok(await fails("select * from public.reserve_credit($1, 'economy')", [p3], /no_credits/),
  "no economy credits — refused");

const p4 = await project(U1, 15);
await reserve(p4);
await db.query("delete from public.projects where id = $1", [p4]);
b = await balance(U1, "premium", 15);
ok(b.available === 9 && b.reserved === 0, "deleting a project with a hold returns the credit");

const p7 = await project(U1, 15);
await reserve(p7);
ok((await one("select public.settle_credit($1, 'release') as r", [p7])).r === true, "site can return a stuck hold");
ok((await one("select public.settle_credit($1, 'release') as r", [p7])).r === false, "second return gives nothing");
ok((await balance(U1, "premium", 15)).available === 9, "balance after a manual return is whole");

ok(await fails("update public.credit_balances set available = -1 where user_id = $1", [U1], /check/),
  "balance can not go below zero");

const o3 = await order(U1, "P5");
await grant(o3);
const p5 = await project(U1, 15);
const r5 = await reserve(p5);
ok(r5.video_sec === 15, "shortest fitting credit is used first");
const p6 = await project(U1, 30);
ok((await reserve(p6)).video_sec === 30, "30 s video takes a 30 s credit");

const ledger = await one(
  `select sum(delta_available)::int a, sum(delta_reserved)::int r from public.credit_ledger where user_id = $1`, [U1]);
const totals = await one(
  "select sum(available)::int a, sum(reserved)::int r from public.credit_balances where user_id = $1", [U1]);
ok(ledger.a === totals.a && ledger.r === totals.r, `ledger adds up to the balance (${totals.a}/${totals.r})`);

// --- права чтения ----------------------------------------------------------
await db.exec(`grant select on all tables in schema public to authenticated, anon;`);
await db.exec(`set role authenticated; set request.jwt.claim.sub = '${U2}';`);
ok((await db.query("select * from public.credit_balances")).rows.length === 0, "other people's balances are hidden");
ok((await db.query("select * from public.orders")).rows.length === 0, "other people's orders are hidden");
ok((await db.query("select * from public.packages")).rows.length === 0, "switched-off packages are hidden");
ok(await fails("select public.grant_order_credits($1, 'manual', null, null, 'me')", [o2], /permission denied/),
  "a user can not grant credits to himself");
ok(await fails("select * from public.reserve_credit($1, 'premium')", [p5], /permission denied/),
  "a user can not call reserve directly");
await db.exec(`set request.jwt.claim.sub = '${U1}';`);
ok((await db.query("select * from public.credit_balances")).rows.length === 2, "own balances are visible");
await db.exec("reset role;");

console.log(failures ? `\n${failures} FAILED` : "\nall passed");
process.exit(failures ? 1 : 0);
