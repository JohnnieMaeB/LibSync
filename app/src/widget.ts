export interface WidgetConfig {
  isWidget: boolean;
  libraryId: string | null;
  // Where "Talk to a librarian" goes — the library's own chat, contact page,
  // email or phone (loader.js `data-help-url`). Null hides the link.
  helpUrl: string | null;
  // Tool groups the library allows (loader.js `data-tools`, e.g.
  // "policies,catalog"), forwarded to the backend as X-LibSync-Tools. Null
  // means all of them. TIER8_PLAN.md §2.8.
  tools: string | null;
}

const HELP_URL_SCHEMES = new Set(["https:", "http:", "mailto:", "tel:"]);

// Only links a patron can safely follow: rejects javascript:, data: and
// anything unparseable, since the value arrives through a URL parameter.
export function safeHelpUrl(raw: string | null | undefined): string | null {
  if (!raw) return null;
  try {
    const url = new URL(raw);
    return HELP_URL_SCHEMES.has(url.protocol) ? url.href : null;
  } catch {
    return null;
  }
}

// Widget mode is driven entirely by the URL loader.js builds for the iframe
// (?mode=widget&library=<id>&help=<url>&tools=<groups>) — see
// app/public/loader.js and TIER6_PLAN.md §2/§3.
export function getWidgetConfig(search: string = window.location.search): WidgetConfig {
  const params = new URLSearchParams(search);
  return {
    isWidget: params.get("mode") === "widget",
    libraryId: params.get("library"),
    helpUrl: safeHelpUrl(params.get("help")),
    tools: params.get("tools")?.trim() || null,
  };
}

// The standalone app's "Talk to a librarian" link, set per deployment.
export function standaloneHelpUrl(): string | null {
  return safeHelpUrl(import.meta.env.VITE_LIBRARY_HELP_URL);
}
