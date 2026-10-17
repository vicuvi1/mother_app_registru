-- Tests for migrations/001_istoric_acces_restaurare.sql — run by CI on a plain
-- Postgres after stubs.sql + schema.sql + the migration. Any failed ASSERT stops
-- the run (psql -v ON_ERROR_STOP=1).
\set QUIET on

-- What Supabase grants by default on new objects in public.
grant usage on schema public to anon, authenticated;
grant all on all tables in schema public to anon, authenticated;
grant all on all sequences in schema public to anon, authenticated;

-- The migration must be safe to run twice.
\i migrations/001_istoric_acces_restaurare.sql

\echo '== allowlist seeded from existing accounts (lower-case), only on the first run'
do $$ begin
  assert (select count(*) from utilizatori_permisi) = 2, 'both existing accounts seeded';
  assert exists (select 1 from utilizatori_permisi where email = 'mama@test.md'), 'email lower-cased';
end $$;
-- The admin reviews the list and removes the stranger.
delete from utilizatori_permisi where email = 'strain@rau.com';
\i migrations/001_istoric_acces_restaurare.sql
do $$ begin assert (select count(*) from utilizatori_permisi) = 1, 're-running does not bring the stranger back'; end $$;

-- Some data, written by the admin (SQL editor).
insert into evidenta_utilizatori (an, luna, data, adulti) values (2026, 10, '01.10', 5), (2026, 10, '02.10', 7);
insert into instruiri (an, luna, data, categorie_varsta, total_participanti, tema_instruirii) values (2026, 10, '03.10', 'copii', 12, 'Cultura informației');

\echo '== approved librarian: full access'
set role authenticated;
select set_config('request.jwt.claims', '{"email":"MAMA@test.md","role":"authenticated"}', false);
do $$ begin
  assert public.is_allowed(), 'mama is allowed (email case ignored)';
  assert (select count(*) from evidenta_utilizatori) = 2, 'mama sees the rows';
end $$;
update evidenta_utilizatori set adulti = 6 where data = '01.10';
update evidenta_utilizatori set adulti = 8 where data = '01.10';   -- typing continues
update evidenta_utilizatori set adulti = 8 where data = '01.10';   -- no real change
update evidenta_utilizatori set pensionari = 2 where data = '01.10';
insert into evidenta_utilizatori (an, luna, data) values (2026, 10, '05.10');
delete from evidenta_utilizatori where data = '02.10';
-- navigation state + a real setting
insert into app_settings (cheie, valoare) values ('session_state', '{"part":"instruiri"}') on conflict (cheie) do update set valoare = excluded.valoare;
insert into app_settings (cheie, valoare) values ('session_state', '{"part":"voluntariat"}') on conflict (cheie) do update set valoare = excluded.valoare;
insert into app_settings (cheie, valoare) values ('excluded_days_2026', '{"10":["14.10"]}') on conflict (cheie) do update set valoare = excluded.valoare;
do $$ begin
  assert (select count(*) from istoric) >= 3, 'mama can read the history';
  assert (select count(*) from istoric where tabel = 'app_settings' and coalesce(ident ->> 'cheie', '') = 'session_state') = 0, 'navigation state is not history';
  assert (select count(*) from istoric where tabel = 'app_settings' and ident ->> 'cheie' = 'excluded_days_2026') = 1, 'real settings are history';
end $$;

\echo '== stranger with a valid login: sees nothing, changes nothing'
select set_config('request.jwt.claims', '{"email":"strain@rau.com","role":"authenticated"}', false);
do $$
declare n integer;
begin
  assert not public.is_allowed(), 'stranger not allowed';
  assert (select count(*) from evidenta_utilizatori) = 0, 'stranger sees no rows';
  assert (select count(*) from istoric) = 0, 'stranger sees no history';
  assert (select count(*) from utilizatori_permisi) = 0, 'stranger cannot read the allowlist';
  update evidenta_utilizatori set adulti = 999; get diagnostics n = row_count;
  assert n = 0, 'stranger update changes nothing';
  delete from evidenta_utilizatori; get diagnostics n = row_count;
  assert n = 0, 'stranger delete removes nothing';
  begin
    insert into evidenta_utilizatori (an, luna, data) values (2026, 10, '09.10');
    assert false, 'stranger insert must fail';
  exception when insufficient_privilege then null; end;
  begin
    perform public.restore_tables('{"tables":{}}'::jsonb, array['voluntariat']);
    assert false, 'stranger restore must fail';
  exception when insufficient_privilege then null; end;
  begin
    perform public.istoric_prune(30);
    assert false, 'app users cannot prune history';
  exception when insufficient_privilege then null; end;
end $$;
reset role;

\echo '== history content'
do $$
declare r record; n integer;
begin
  select count(*) into n from istoric where tabel = 'evidenta_utilizatori' and operatie = 'UPDATE';
  assert n = 1, format('typing burst merged into ONE history entry (got %s)', n);
  select * into r from istoric where tabel = 'evidenta_utilizatori' and operatie = 'UPDATE';
  assert r.utilizator = 'mama@test.md', 'who: ' || coalesce(r.utilizator, 'null');
  assert r.vechi = '{"adulti": 5, "pensionari": 0}'::jsonb, 'vechi keeps the values from before the burst: ' || r.vechi::text;
  assert r.nou = '{"adulti": 8, "pensionari": 2}'::jsonb, 'nou has the latest values: ' || r.nou::text;
  assert not (r.vechi ? 'updated_at'), 'updated_at is not history';
  select * into r from istoric where operatie = 'DELETE';
  assert r.vechi ->> 'data' = '02.10' and (r.vechi ->> 'adulti')::int = 7, 'DELETE keeps the whole row';
  select * into r from istoric where operatie = 'INSERT' and utilizator = 'mama@test.md';
  assert r.ident = '{"an": 2026, "luna": 10, "data": "05.10"}'::jsonb, 'INSERT keeps identifying fields: ' || r.ident::text;
  select * into r from istoric where tabel = 'evidenta_utilizatori' and operatie = 'UPDATE';
  assert r.ident ->> 'data' = '01.10', 'UPDATE says which row: ' || coalesce(r.ident::text, 'null');
end $$;

\echo '== a deleted row can be brought back from history with its id'
insert into evidenta_utilizatori select * from jsonb_populate_record(null::evidenta_utilizatori, (select vechi from istoric where operatie = 'DELETE'));
do $$ begin assert (select adulti from evidenta_utilizatori where data = '02.10') = 7, 'row back'; end $$;

\echo '== restore: all-or-nothing, original ids, id counters moved past them'
create temp table snap as
  select jsonb_build_object('created', '2026-10-01T10:00:00Z', 'tables', jsonb_build_object(
    'evidenta_utilizatori', (select jsonb_agg(to_jsonb(e)) from evidenta_utilizatori e),
    'instruiri', (select jsonb_agg(to_jsonb(i) - 'tineri_17_34') from instruiri i)  -- an older copy may lack a column
  )) as p;
grant select on snap to authenticated;
update evidenta_utilizatori set adulti = 0;
delete from instruiri;
insert into instruiri (an, luna, data, categorie_varsta) values (2026, 10, '20.10', 'adulti');
set role authenticated;
select set_config('request.jwt.claims', '{"email":"mama@test.md","role":"authenticated"}', false);
select public.restore_tables((select p from snap), array['evidenta_utilizatori', 'instruiri']) as restored \gset
reset role;
do $$
declare before_max bigint; new_id bigint;
begin
  assert (select adulti from evidenta_utilizatori where data = '01.10') = 8, 'values restored';
  assert (select count(*) from instruiri) = 1 and (select tema_instruirii from instruiri) = 'Cultura informației', 'instruiri restored exactly (extra row removed)';
  assert (select tineri_17_34 from instruiri) = 0, 'column missing from the copy gets its default';
  select max(id) into before_max from evidenta_utilizatori;
  insert into evidenta_utilizatori (an, luna, data) values (2026, 10, '30.10') returning id into new_id;
  assert new_id > before_max, 'new rows do not collide with restored ids';
  assert (select count(*) from istoric where operatie = 'RESTORE') = 1, 'one RESTORE entry';
  assert (select count(*) from istoric where tabel = 'instruiri' and la > now() - interval '1 minute' and operatie = 'DELETE') = 1, 'only the pre-restore manual delete was logged, not the restore itself';
end $$;

-- A copy that breaks halfway (text in a number column, 2nd table) changes NOTHING.
update evidenta_utilizatori set adulti = 1 where data = '01.10';
set role authenticated;
select set_config('request.jwt.claims', '{"email":"mama@test.md","role":"authenticated"}', false);
do $$ begin
  begin
    perform public.restore_tables(
      jsonb_build_object('tables', jsonb_build_object(
        'evidenta_utilizatori', jsonb_build_array(jsonb_build_object('id', 1, 'an', 2026, 'luna', 10, 'data', '01.10', 'adulti', 50)),
        'voluntariat', jsonb_build_array(jsonb_build_object('id', 1, 'nume_prenume', 'X', 'numar_ore', 'multe')))),
      array['evidenta_utilizatori', 'voluntariat']);
    assert false, 'broken copy must raise';
  exception when invalid_text_representation then null; end;
end $$;
reset role;
do $$ begin
  assert (select adulti from evidenta_utilizatori where data = '01.10') = 1, 'first table untouched after the failed restore';
  assert (select count(*) from evidenta_utilizatori) = 4, 'no rows lost after the failed restore';
end $$;

\echo '== prune keeps recent history'
insert into istoric (la, tabel, operatie) values (now() - interval '800 days', 'x', 'UPDATE');
do $$ begin
  assert public.istoric_prune(730) = 1, 'old entry pruned';
  assert (select count(*) from istoric) > 0, 'recent entries kept';
end $$;

\echo 'MIGRATION 001 TESTS PASSED'
