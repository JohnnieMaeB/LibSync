import { useEffect, useState } from "react";
import { API_BASE_URL } from "./config";
import { safeHelpUrl } from "./widget";

// A library's dashboard settings (Tier 8 Phase 30), from GET /libraries/{id}.
// The backend answers 404 when there are none (including when Supabase isn't
// set up), and then the embed snippet's attributes apply as before.
export interface PublicLibraryConfig {
  id: string;
  name: string;
  helpUrl: string | null;
  aiEnabled: boolean;
  feedbackEnabled: boolean;
}

export async function fetchLibraryConfig(libraryId: string): Promise<PublicLibraryConfig | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/libraries/${encodeURIComponent(libraryId)}`);
    if (!response.ok) return null;
    const data = await response.json();
    return {
      id: data.id,
      name: data.name,
      helpUrl: safeHelpUrl(data.help_url),
      aiEnabled: data.ai_enabled !== false,
      feedbackEnabled: data.feedback_enabled === true,
    };
  } catch {
    return null; // offline or backend asleep: never block the chat on settings
  }
}

export function useLibraryConfig(libraryId: string | null): PublicLibraryConfig | null {
  const [config, setConfig] = useState<PublicLibraryConfig | null>(null);
  useEffect(() => {
    if (!libraryId) return;
    let cancelled = false;
    fetchLibraryConfig(libraryId).then((result) => {
      if (!cancelled) setConfig(result);
    });
    return () => {
      cancelled = true;
    };
  }, [libraryId]);
  return config;
}
