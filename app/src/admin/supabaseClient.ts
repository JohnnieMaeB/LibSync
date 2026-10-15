import { createClient, type SupabaseClient } from "@supabase/supabase-js";

// The staff dashboard's Supabase client (Tier 8 Phase 30). Both values are
// public by design (the publishable key only grants what row-level security
// allows); without them the dashboard says it isn't set up, and nothing else
// in the app changes.
let client: SupabaseClient | null | undefined;

export function getSupabase(): SupabaseClient | null {
  if (client !== undefined) return client;
  const url = import.meta.env.VITE_SUPABASE_URL;
  const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;
  client = url && key ? createClient(url, key) : null;
  return client;
}
