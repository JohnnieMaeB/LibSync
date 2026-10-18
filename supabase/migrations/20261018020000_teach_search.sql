-- Information literacy (NEXT_FEATURES.md P1.4): a library can open "How I found
-- this" under every answer by default ("teach the search").
alter table public.libraries add column if not exists teach_search boolean not null default false;
