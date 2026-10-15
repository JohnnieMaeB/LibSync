/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  // Standalone app's "Talk to a librarian" link (https:, mailto: or tel:).
  readonly VITE_LIBRARY_HELP_URL?: string;
}
