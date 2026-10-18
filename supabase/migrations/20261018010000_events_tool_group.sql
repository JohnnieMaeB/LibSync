-- LibCal events (NEXT_FEATURES.md 11): a library can switch off the events tool.
alter table public.libraries drop constraint libraries_enabled_tools_check;
alter table public.libraries add constraint libraries_enabled_tools_check
  check (enabled_tools is null
         or enabled_tools <@ array['policies','catalog','recommendations','research','citations','ebooks','rooms','events','account']);
