import { describe, expect, it } from "vitest";
import { isMiss, shouldOfferHandoff } from "./handoff";
import type { BotEntry, ChatEntry } from "../types";

function bot(text: string, extra: Partial<BotEntry> = {}): BotEntry {
  return {
    kind: "bot",
    id: Math.random().toString(),
    status: "done",
    blocks: text ? [{ type: "text", key: "k", text }] : [],
    cardCount: 0,
    isLatest: false,
    ...extra,
  };
}
const user: ChatEntry = { kind: "user", id: "u", text: "q" };

describe("staff handoff", () => {
  it("counts errors, empty replies and admitted gaps as misses, in English and Spanish", () => {
    expect(isMiss(bot("", { status: "error" }))).toBe(true);
    expect(isMiss(bot(""))).toBe(true);
    expect(isMiss(bot("Sorry, I couldn’t find anything about that in the library's policies."))).toBe(true);
    expect(isMiss(bot("Lo siento, no encontré esa información."))).toBe(true);
    expect(isMiss(bot("You can renew up to three times."))).toBe(false);
    expect(isMiss(bot("I don't have that title, but here are similar ones.", { cardCount: 3 }))).toBe(false);
    expect(isMiss(bot("", { status: "streaming" }))).toBe(false);
  });

  it("offers a person after two misses, and withdraws it after a good answer", () => {
    const miss = bot("I don't have information about that.");
    const good = bot("You can renew up to three times.");
    expect(shouldOfferHandoff([user, miss])).toBe(false);
    expect(shouldOfferHandoff([user, miss, user, miss])).toBe(true);
    expect(shouldOfferHandoff([user, miss, user, miss, user, good])).toBe(false);
  });
});
