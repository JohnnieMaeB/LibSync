export interface WidgetConfig {
  isWidget: boolean;
  libraryId: string | null;
}

// Widget mode is driven entirely by the URL loader.js builds for the iframe
// (?mode=widget&library=<id>) — see app/public/loader.js and TIER6_PLAN.md §2/§3.
export function getWidgetConfig(search: string = window.location.search): WidgetConfig {
  const params = new URLSearchParams(search);
  return {
    isWidget: params.get("mode") === "widget",
    libraryId: params.get("library"),
  };
}
