-- Readers' advisory (NEXT_FEATURES.md P1.5): a library can switch off book
-- recommendations separately from catalog search.
alter table public.libraries drop constraint libraries_enabled_tools_check;
alter table public.libraries add constraint libraries_enabled_tools_check
  check (enabled_tools is null
         or enabled_tools <@ array['policies','catalog','recommendations','research','citations','ebooks','rooms','account']);
