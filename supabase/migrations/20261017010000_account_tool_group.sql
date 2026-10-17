-- Tier 9 Phase 38: a library can switch off the signed-in patron account tool.
alter table public.libraries drop constraint libraries_enabled_tools_check;
alter table public.libraries add constraint libraries_enabled_tools_check
  check (enabled_tools is null
         or enabled_tools <@ array['policies','catalog','research','citations','ebooks','rooms','account']);
