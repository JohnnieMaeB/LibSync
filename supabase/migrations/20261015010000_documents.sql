-- Tier 8 Phase 31: metadata for each library's uploaded policy documents. The
-- text itself lives as chunks in the library's Pinecone namespace; the
-- original file is not stored. Rows are written only by the backend (secret
-- key); staff can read their own library's list.

create table public.library_documents (
  id text primary key,
  library_id text not null references public.libraries (id) on delete cascade,
  name text not null,
  chunk_count integer not null check (chunk_count > 0),
  uploaded_by uuid references auth.users (id) on delete set null,
  created_at timestamptz not null default now()
);

create index library_documents_library_idx on public.library_documents (library_id, name);

alter table public.library_documents enable row level security;

create policy "staff read their library's documents" on public.library_documents
  for select to authenticated using (public.is_library_staff(library_id));
