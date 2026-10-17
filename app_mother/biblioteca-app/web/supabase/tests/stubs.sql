-- Stand-ins for the Supabase objects that schema.sql and the migrations refer to,
-- so they can be tested on a plain Postgres (CI). Never run this on Supabase.
do $$ begin create role anon nologin; exception when duplicate_object then null; end $$;
do $$ begin create role authenticated nologin; exception when duplicate_object then null; end $$;
do $$ begin create role service_role nologin; exception when duplicate_object then null; end $$;

create schema if not exists auth;
create table if not exists auth.users (id bigserial primary key, email text, created_at timestamptz default now(), last_sign_in_at timestamptz);
create schema if not exists storage;
create table if not exists storage.buckets (id text primary key, name text, public boolean);
create table if not exists storage.objects (id bigserial primary key, bucket_id text, name text);

-- Two accounts exist before the migration: the librarian and a stranger who signed
-- up while sign-ups were open.
insert into auth.users (email) values ('Mama@Test.md'), ('strain@rau.com');
