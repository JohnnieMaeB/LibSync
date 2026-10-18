// Information literacy (NEXT_FEATURES.md P1.4): every grounded answer can show
// how it was found, so a patron sees the search behind it and can repeat it.
// Built from the AG-UI tool-call events the stream already carries (name plus
// JSON arguments), so it costs no model calls and can't be embellished.

import type { Messages } from "../i18n/messages";
import type { SearchStep } from "../types";

// Tools the patron never needs to see: pydantic-ai's structured-output tool,
// and names the model sometimes invents (a call to them is just retried).
const DESCRIBED = new Set([
  "search_library_policies",
  "search_catalog",
  "recommend_books",
  "search_scholarly_works",
  "lookup_and_cite",
  "check_ebook_availability",
  "check_room_availability",
  "check_library_events",
  "check_my_account",
]);

function text(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

// One step from a finished tool call, or null for calls not worth showing.
export function stepFromToolCall(tool: string, rawArgs: string): SearchStep | null {
  if (!DESCRIBED.has(tool)) return null;
  let args: Record<string, unknown> = {};
  try {
    const parsed = JSON.parse(rawArgs || "{}");
    if (parsed && typeof parsed === "object") args = parsed;
  } catch {
    // Arguments that don't parse still say which source was searched.
  }
  const query = text(args.query) || text(args.search) || text(args.like) || text(args.about) || text(args.title) || text(args.doi) || text(args.date);
  return { tool, query, mode: text(args.like) ? "like" : undefined };
}

export function describeStep(step: SearchStep, t: Messages): string {
  const describe = t.searchSteps[step.mode === "like" ? "recommend_books_like" : step.tool];
  return describe ? describe(step.query) : t.searchSteps.other(step.query);
}
