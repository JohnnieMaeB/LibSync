// Staff handoff (NEXT_FEATURES.md, research October 2026): after the assistant
// has failed a patron twice in one conversation, offer a person instead of a
// third try, as Virginia Beach Public Library's chatbot does. A "miss" is an
// error, an empty reply, or a reply admitting it couldn't help, with no cards.

import type { BotEntry, ChatEntry } from "../types";

// Phrases an answer uses when it couldn't help, in English and Spanish.
// Broad on purpose: a false positive only offers a librarian a bit early.
const ADMITS_GAP =
  /\b(I (?:don['’]t|do not) have|I (?:couldn['’]t|could not|can['’]t|cannot) find|I (?:wasn['’]t|was not|am not|['’]m not) able|no information (?:about|on)|(?:isn['’]t|is not|not) covered|doesn['’]t (?:cover|mention)|no tengo|no (?:pude|puedo) encontrar|no encontr[ée]|no hay información|no (?:cubre|menciona))(?![a-záéíóúñ])/i;

export const MISSES_BEFORE_HANDOFF = 2;

export function isMiss(entry: BotEntry): boolean {
  if (entry.status === "error") return true;
  if (entry.status !== "done") return false;
  if (entry.cardCount > 0) return false;
  if (entry.blocks.length === 0) return true;
  return entry.blocks.some((block) => block.type === "text" && ADMITS_GAP.test(block.text));
}

// Offer a person once the conversation has this many misses and the latest
// reply is one of them (a later good answer withdraws the offer).
export function shouldOfferHandoff(entries: ChatEntry[]): boolean {
  const bots = entries.filter((e): e is BotEntry => e.kind === "bot");
  const latest = bots[bots.length - 1];
  if (!latest || !isMiss(latest)) return false;
  return bots.filter(isMiss).length >= MISSES_BEFORE_HANDOFF;
}
