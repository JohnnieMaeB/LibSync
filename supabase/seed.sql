-- A demo library for pilots and walkthroughs (docs/PILOT.md). Run after the
-- migrations: `supabase db reset` applies it locally, or paste it into the SQL
-- editor. It uses only public sources: LibSync's demo policies (the default
-- Pinecone namespace) and Open Library, so it needs no vendor credentials.
insert into public.libraries (id, name, help_url, ai_enabled, catalog_driver, teach_search)
values ('demo-public-library', 'Demo Public Library', 'mailto:ask@library.example', true, 'openlibrary', true)
on conflict (id) do update
  set name = excluded.name,
      help_url = excluded.help_url,
      ai_enabled = excluded.ai_enabled,
      catalog_driver = excluded.catalog_driver,
      teach_search = excluded.teach_search;

-- Give a staff member access after they first sign in to the dashboard:
-- insert into public.library_staff (library_id, user_id)
-- select 'demo-public-library', id from auth.users where email = 'you@library.example';
