/// <reference types="vite/client" />
/// <reference types="vite-plugin-pwa/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  // Standalone app's "Talk to a librarian" link (https:, mailto: or tel:).
  readonly VITE_LIBRARY_HELP_URL?: string;
  // Staff dashboard (Tier 8). Both public by design; unset = dashboard off.
  readonly VITE_SUPABASE_URL?: string;
  readonly VITE_SUPABASE_PUBLISHABLE_KEY?: string;
  // Tier 9: a deployment dedicated to one library.
  readonly VITE_LIBRARY_ID?: string;
}
