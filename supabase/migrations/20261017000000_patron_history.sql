-- Tier 9 Phase 37: chat history for patrons who chose to sign in, so it
-- follows them across devices. Keyed by LibSync's one-way patron reference
-- (never a card number or email). Only the backend reads or writes it: RLS
-- is on with no policies, so the publishable key can't reach it at all.
-- Rows untouched for 90 days are deleted (enforced by the backend).

create table public.patron_conversations (
  patron_ref text not null,
  library_id text not null references public.libraries (id) on delete cascade,
  id text not null,
  title text not null,
  created_at_ms bigint not null,
  updated_at_ms bigint not null,
  entries jsonb not null,
  updated_at timestamptz not null default now(),
  primary key (patron_ref, id)
);

create index patron_conversations_age_idx on public.patron_conversations (updated_at);

alter table public.patron_conversations enable row level security;
