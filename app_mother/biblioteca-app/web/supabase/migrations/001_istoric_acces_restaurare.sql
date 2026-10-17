-- ============================================================================
-- Migrarea 001 — istoric modificări, acces doar pentru conturi aprobate,
-- restaurare sigură (totul-sau-nimic).
-- ----------------------------------------------------------------------------
-- Cum se rulează: Supabase → SQL Editor → New query → lipiți TOT fișierul → Run.
-- Se poate rula de mai multe ori fără probleme (idempotent).
-- La final, tabelul afișat = conturile care au acces. Dacă vedeți un email
-- necunoscut, ștergeți-l (vezi comanda de la sfârșitul fișierului).
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. Conturi aprobate (allowlist)
-- ---------------------------------------------------------------------------
create table if not exists public.utilizatori_permisi (
  email   text primary key check (email = lower(email)),
  rol     text not null default 'bibliotecar',
  adaugat timestamptz not null default now()
);
alter table public.utilizatori_permisi enable row level security;

-- Emailul utilizatorului din cererea curentă (din token-ul de login). În SQL Editor = 'postgres'.
create or replace function public.current_email()
returns text language sql stable as $$
  select coalesce(lower(nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'email'), session_user::text)
$$;

-- Are utilizatorul curent acces la registru?
create or replace function public.is_allowed()
returns boolean language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.utilizatori_permisi where email = public.current_email())
$$;
revoke all on function public.is_allowed() from public;
grant execute on function public.is_allowed() to anon, authenticated;

-- Prima rulare: aprobă conturile existente (cele create de dvs. în Authentication → Users).
-- La rulările următoare nu mai adaugă nimic (ca să nu reapară cineva șters).
insert into public.utilizatori_permisi (email)
select distinct lower(u.email) from auth.users u
where u.email is not null and not exists (select 1 from public.utilizatori_permisi)
on conflict do nothing;

drop policy if exists p_read_self on public.utilizatori_permisi;
create policy p_read_self on public.utilizatori_permisi for select to authenticated using (public.is_allowed());

-- ---------------------------------------------------------------------------
-- 2. Politici: în loc de „orice cont autentificat", doar conturile aprobate
-- ---------------------------------------------------------------------------
do $$
declare t text;
begin
  foreach t in array array[
    'personal','range_config','etichete_custom','app_settings','text_presets',
    'evidenta_utilizatori','evidenta_utilizatori_copii_adulti','documente_inregistrate',
    'documente_continut_czu','cercetari_bibliografice','activitati_informare',
    'documente_electronice','instruiri','activitati_culturale','activitati_online',
    'parteneri','voluntariat'
  ]
  loop
    execute format('alter table public.%I enable row level security;', t);
    execute format('drop policy if exists p_auth_all on public.%I;', t);
    execute format('drop policy if exists p_allowed_all on public.%I;', t);
    execute format('create policy p_allowed_all on public.%I for all to authenticated using (public.is_allowed()) with check (public.is_allowed());', t);
  end loop;
end $$;

-- Copiile din cloud (bucket „backups"): tot doar conturile aprobate.
drop policy if exists "backups_auth_read" on storage.objects;
drop policy if exists "backups_auth_insert" on storage.objects;
drop policy if exists "backups_auth_delete" on storage.objects;
drop policy if exists "backups_allowed_read" on storage.objects;
drop policy if exists "backups_allowed_insert" on storage.objects;
drop policy if exists "backups_allowed_delete" on storage.objects;
create policy "backups_allowed_read" on storage.objects for select to authenticated using (bucket_id = 'backups' and public.is_allowed());
create policy "backups_allowed_insert" on storage.objects for insert to authenticated with check (bucket_id = 'backups' and public.is_allowed());
create policy "backups_allowed_delete" on storage.objects for delete to authenticated using (bucket_id = 'backups' and public.is_allowed());

-- ---------------------------------------------------------------------------
-- 3. Istoric modificări — fiecare adăugare / modificare / ștergere, cu cine și când
-- ---------------------------------------------------------------------------
create table if not exists public.istoric (
  id         bigint generated always as identity primary key,
  la         timestamptz not null default now(),
  utilizator text,
  tabel      text not null,
  rand_id    bigint,
  operatie   text not null,  -- INSERT | UPDATE | DELETE | RESTORE
  vechi      jsonb,          -- UPDATE: valorile de dinainte (doar câmpurile schimbate) · DELETE: tot rândul
  nou        jsonb           -- UPDATE: valorile noi · INSERT: câmpurile de identificare
);
create index if not exists istoric_la_idx on public.istoric (la desc);
create index if not exists istoric_rand_idx on public.istoric (tabel, rand_id, id desc);
alter table public.istoric enable row level security;
drop policy if exists p_istoric_read on public.istoric;
create policy p_istoric_read on public.istoric for select to authenticated using (public.is_allowed());
-- (nicio politică de scriere: istoricul se scrie doar de trigger, nu din aplicație)

create or replace function public.istoric_log()
returns trigger language plpgsql security definer set search_path = public as $$
declare
  usr text := public.current_email();
  o jsonb; n jsonb; vd jsonb := '{}'; nd jsonb := '{}'; k text; last_id bigint; rid bigint;
  ignore_keys text[] := array['updated_at', 'created_at'];
  ident_keys text[] := array['an', 'luna', 'data', 'categorie_varsta', 'nume_prenume', 'partener', 'cheie', 'parte', 'camp', 'valoare'];
begin
  -- În timpul unei restaurări se scrie o singură intrare (RESTORE), nu mii.
  if current_setting('app.restoring', true) = 'on' then return null; end if;
  -- „unde am rămas" se scrie la fiecare navigare — nu e o modificare a registrului
  if tg_table_name = 'app_settings' then
    if (case when tg_op = 'DELETE' then to_jsonb(old) else to_jsonb(new) end) ->> 'cheie' in ('session_state', 'seeded_v1') then return null; end if;
  end if;

  if tg_op = 'UPDATE' then
    o := to_jsonb(old); n := to_jsonb(new);
    for k in select jsonb_object_keys(n) loop
      if k = any(ignore_keys) then continue; end if;
      if (o -> k) is distinct from (n -> k) then vd := vd || jsonb_build_object(k, o -> k); nd := nd || jsonb_build_object(k, n -> k); end if;
    end loop;
    if nd = '{}'::jsonb then return null; end if;
    rid := (n ->> 'id')::bigint;
    -- Scrierea „din mers" (fiecare tastă) se adună într-o singură intrare: același
    -- utilizator, același rând, în ultimele 2 minute. „vechi" păstrează valoarea de la început.
    select id into last_id from public.istoric
      where tabel = tg_table_name and rand_id = rid and operatie = 'UPDATE'
        and utilizator is not distinct from usr and la > now() - interval '2 minutes'
      order by id desc limit 1;
    if last_id is not null then
      update public.istoric set nou = nou || nd, vechi = vd || vechi, la = now() where id = last_id;
    else
      insert into public.istoric (utilizator, tabel, rand_id, operatie, vechi, nou) values (usr, tg_table_name, rid, 'UPDATE', vd, nd);
    end if;
    return null;
  elsif tg_op = 'INSERT' then
    n := to_jsonb(new);
    for k in select jsonb_object_keys(n) loop if k = any(ident_keys) then nd := nd || jsonb_build_object(k, n -> k); end if; end loop;
    insert into public.istoric (utilizator, tabel, rand_id, operatie, nou) values (usr, tg_table_name, (n ->> 'id')::bigint, 'INSERT', nd);
    return null;
  else -- DELETE: tot rândul, ca să poată fi readus
    o := to_jsonb(old);
    insert into public.istoric (utilizator, tabel, rand_id, operatie, vechi) values (usr, tg_table_name, (o ->> 'id')::bigint, 'DELETE', o);
    return null;
  end if;
end $$;

do $$
declare t text;
begin
  foreach t in array array[
    'personal','range_config','etichete_custom','app_settings','text_presets',
    'evidenta_utilizatori','evidenta_utilizatori_copii_adulti','documente_inregistrate',
    'documente_continut_czu','cercetari_bibliografice','activitati_informare',
    'documente_electronice','instruiri','activitati_culturale','activitati_online',
    'parteneri','voluntariat'
  ]
  loop
    execute format('drop trigger if exists trg_%1$s_istoric on public.%1$I;', t);
    execute format('create trigger trg_%1$s_istoric after insert or update or delete on public.%1$I for each row execute function public.istoric_log();', t);
  end loop;
end $$;

-- Curățenie: păstrează istoricul pe ultimele N zile (rulat noaptea de jobul de backup;
-- intrările mai vechi rămân oricum în copiile zilnice din GitHub).
create or replace function public.istoric_prune(zile integer default 730)
returns integer language plpgsql security definer set search_path = public as $$
declare n integer;
begin
  delete from public.istoric where la < now() - make_interval(days => greatest(zile, 30));
  get diagnostics n = row_count;
  return n;
end $$;
revoke all on function public.istoric_prune(integer) from public, anon, authenticated;

-- ---------------------------------------------------------------------------
-- 4. Restaurare sigură: înlocuiește tabelele alese cu cele dintr-o copie,
--    TOTUL-SAU-NIMIC (dacă ceva eșuează, nu se schimbă nimic), cu id-urile
--    originale, și mută contoarele de id după cele restaurate.
-- ---------------------------------------------------------------------------
create or replace function public.restore_tables(payload jsonb, tabele text[])
returns jsonb language plpgsql security definer set search_path = public as $$
declare
  t text; arr jsonb; cols text; n integer; res jsonb := '{}';
  permise text[] := array[
    'personal','range_config','etichete_custom','app_settings','text_presets',
    'evidenta_utilizatori','evidenta_utilizatori_copii_adulti','documente_inregistrate',
    'documente_continut_czu','cercetari_bibliografice','activitati_informare',
    'documente_electronice','instruiri','activitati_culturale','activitati_online',
    'parteneri','voluntariat'];
begin
  if not public.is_allowed() then raise exception 'Acces interzis' using errcode = '42501'; end if;
  if tabele is null or cardinality(tabele) = 0 then raise exception 'Nu ați ales nicio parte de restaurat'; end if;
  perform set_config('app.restoring', 'on', true);
  foreach t in array tabele loop
    if not t = any(permise) then raise exception 'Tabel necunoscut: %', t; end if;
    arr := coalesce(payload -> 'tables' -> t, '[]'::jsonb);
    if jsonb_typeof(arr) <> 'array' then raise exception 'Copie invalidă pentru %', t; end if;
    execute format('delete from public.%I', t);
    -- doar coloanele prezente în copie (cele lipsă primesc valoarea implicită)
    select string_agg(quote_ident(c.column_name), ', ' order by c.ordinal_position) into cols
      from information_schema.columns c
      where c.table_schema = 'public' and c.table_name = t
        and c.column_name in (select distinct jsonb_object_keys(e) from jsonb_array_elements(arr) e);
    n := 0;
    if cols is not null then
      execute format('insert into public.%1$I (%2$s) overriding system value select %2$s from jsonb_populate_recordset(null::public.%1$I, $1)', t, cols) using arr;
      get diagnostics n = row_count;
    end if;
    if exists (select 1 from information_schema.columns where table_schema = 'public' and table_name = t and column_name = 'id') then
      execute format('select setval(pg_get_serial_sequence(%L, ''id''), coalesce((select max(id) from public.%I), 0) + 1, false)', 'public.' || t, t);
    end if;
    res := res || jsonb_build_object(t, n);
  end loop;
  perform set_config('app.restoring', 'off', true);
  insert into public.istoric (utilizator, tabel, operatie, nou)
    values (public.current_email(), '*', 'RESTORE', jsonb_build_object('tabele', to_jsonb(tabele), 'randuri', res, 'copia_din', payload ->> 'created'));
  return res;
end $$;
revoke all on function public.restore_tables(jsonb, text[]) from public;
grant execute on function public.restore_tables(jsonb, text[]) to authenticated;

-- ---------------------------------------------------------------------------
-- Rezultat: cine are acces acum. Necunoscut? Ștergeți-l:
--   delete from public.utilizatori_permisi where email = 'adresa@necunoscuta.com';
-- Adăugare cont nou (după ce îl creați în Authentication → Users):
--   insert into public.utilizatori_permisi (email) values ('nume@exemplu.com');
-- ---------------------------------------------------------------------------
select p.email, p.adaugat, u.created_at as cont_creat, u.last_sign_in_at as ultima_autentificare
from public.utilizatori_permisi p left join auth.users u on lower(u.email) = p.email
order by p.email;
