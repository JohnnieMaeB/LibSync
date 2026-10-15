-- Tier 8 Phase 30: per-library configuration and staff membership.
-- TIER8_PLAN.md §2.2. Row-level security (RLS) enforces that staff only ever
-- see and change their own library, whatever the app code does.

create table public.libraries (
  id text primary key
    check (id ~ '^[a-z0-9][a-z0-9-]{0,62}$'),          -- same slug rule as app/tenants.py
  name text not null,
  -- Patron-facing settings, mirrored by GET /libraries/{id} on the backend.
  help_url text
    check (help_url is null or help_url ~* '^(https?:|mailto:|tel:)'),
  enabled_tools text[]                                  -- null = every tool group
    check (enabled_tools is null or enabled_tools <@ array['policies','catalog','research','citations']),
  ai_enabled boolean not null default true,             -- ALA AI guidance: the library can switch AI off
  allowed_origins text[],                               -- null = any origin may embed the widget
  catalog_driver text not null default 'openlibrary',
  catalog_config jsonb not null default '{}'::jsonb,    -- non-secret driver settings (base URL etc.)
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.library_staff (
  library_id text not null references public.libraries (id) on delete cascade,
  user_id uuid not null references auth.users (id) on delete cascade,
  role text not null default 'staff' check (role in ('admin', 'staff')),
  primary key (library_id, user_id)
);

-- Integration credentials (ILS API keys, Springshare client secrets). Staff
-- may write them but never read them back; only the backend's secret key
-- (which bypasses RLS) reads this table.
create table public.library_secrets (
  library_id text not null references public.libraries (id) on delete cascade,
  name text not null,
  value text not null,
  updated_at timestamptz not null default now(),
  primary key (library_id, name)
);

alter table public.libraries enable row level security;
alter table public.library_staff enable row level security;
alter table public.library_secrets enable row level security;

create function public.is_library_staff(target text, admin_only boolean default false)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.library_staff
    where library_id = target
      and user_id = auth.uid()
      and (not admin_only or role = 'admin')
  );
$$;

create policy "staff read their library" on public.libraries
  for select to authenticated using (public.is_library_staff(id));
create policy "staff update their library" on public.libraries
  for update to authenticated using (public.is_library_staff(id)) with check (public.is_library_staff(id));

create policy "staff see their library's staff" on public.library_staff
  for select to authenticated using (public.is_library_staff(library_id));
create policy "admins manage staff" on public.library_staff
  for all to authenticated
  using (public.is_library_staff(library_id, true))
  with check (public.is_library_staff(library_id, true));

create policy "admins write secrets" on public.library_secrets
  for insert to authenticated with check (public.is_library_staff(library_id, true));
create policy "admins replace secrets" on public.library_secrets
  for update to authenticated
  using (public.is_library_staff(library_id, true))
  with check (public.is_library_staff(library_id, true));
create policy "admins delete secrets" on public.library_secrets
  for delete to authenticated using (public.is_library_staff(library_id, true));
-- No select policy: secrets are write-only from the dashboard.

create function public.touch_updated_at() returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;
create trigger libraries_updated_at before update on public.libraries
  for each row execute function public.touch_updated_at();
create trigger library_secrets_updated_at before update on public.library_secrets
  for each row execute function public.touch_updated_at();

-- New libraries are created by the operator (SQL editor or service key), then
-- an admin is added with:
--   insert into public.library_staff (library_id, user_id, role)
--   values ('<library-id>', '<auth user uuid>', 'admin');
