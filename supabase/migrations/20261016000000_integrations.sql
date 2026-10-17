-- Tier 8 Phase 37T: non-secret settings for vendor integrations a library
-- already subscribes to (OverDrive/Libby availability, LibCal rooms). Their
-- client secrets go in library_secrets (write-only), as with catalog drivers.

alter table public.libraries
  add column integrations jsonb not null default '{}'::jsonb;

-- Two new tool groups a library can switch off: ebooks (OverDrive) and rooms (LibCal).
alter table public.libraries drop constraint libraries_enabled_tools_check;
alter table public.libraries add constraint libraries_enabled_tools_check
  check (enabled_tools is null
         or enabled_tools <@ array['policies','catalog','research','citations','ebooks','rooms']);
