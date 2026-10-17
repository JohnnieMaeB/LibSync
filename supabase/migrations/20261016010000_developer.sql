-- Tier 8 Phase 34: per-library API keys for server-to-server use, and an
-- optional webhook that receives patrons' "not helpful" feedback.

create table public.library_api_keys (
  id uuid primary key default gen_random_uuid(),
  library_id text not null references public.libraries (id) on delete cascade,
  name text not null,
  key_hash text not null unique,          -- sha256 of the key; the key itself is shown once and never stored
  prefix text not null,                   -- first characters, so staff can tell keys apart
  created_by uuid references auth.users (id) on delete set null,
  created_at timestamptz not null default now(),
  revoked_at timestamptz
);

alter table public.library_api_keys enable row level security;
-- Rows are written only by the backend (secret key); staff can list theirs.
create policy "staff list their library's keys" on public.library_api_keys
  for select to authenticated using (public.is_library_staff(library_id));

alter table public.libraries
  add column feedback_webhook text check (feedback_webhook is null or feedback_webhook ~* '^https://');
