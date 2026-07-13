import { beforeEach, describe, expect, it } from "vitest";
import { deleteConversation, getConversation, listConversations, putConversation } from "./db";
import type { Conversation } from "../types";

function makeConversation(overrides: Partial<Conversation> = {}): Conversation {
  return {
    id: overrides.id ?? crypto.randomUUID(),
    title: overrides.title ?? "Untitled",
    createdAt: overrides.createdAt ?? Date.now(),
    updatedAt: overrides.updatedAt ?? Date.now(),
    entries: overrides.entries ?? [],
  };
}

describe("db (IndexedDB conversation store)", () => {
  beforeEach(async () => {
    const existing = await listConversations();
    await Promise.all(existing.map((c) => deleteConversation(c.id)));
  });

  it("round-trips a conversation through put/get", async () => {
    const conversation = makeConversation({
      title: "My first chat",
      entries: [{ kind: "user", id: "u1", text: "hi" }],
    });
    await putConversation(conversation);

    const fetched = await getConversation(conversation.id);
    expect(fetched).toEqual(conversation);
  });

  it("returns undefined for a conversation that doesn't exist", async () => {
    expect(await getConversation("nope")).toBeUndefined();
  });

  it("lists conversations newest-first by updatedAt", async () => {
    const older = makeConversation({ id: "a", title: "Older", updatedAt: 1000 });
    const newer = makeConversation({ id: "b", title: "Newer", updatedAt: 2000 });
    await putConversation(older);
    await putConversation(newer);

    const list = await listConversations();
    expect(list.map((c) => c.id)).toEqual(["b", "a"]);
  });

  it("put overwrites an existing conversation with the same id", async () => {
    const conversation = makeConversation({ id: "x", title: "First title" });
    await putConversation(conversation);
    await putConversation({ ...conversation, title: "Renamed" });

    const fetched = await getConversation("x");
    expect(fetched?.title).toBe("Renamed");
    expect(await listConversations()).toHaveLength(1);
  });

  it("deletes a conversation", async () => {
    const conversation = makeConversation({ id: "to-delete" });
    await putConversation(conversation);
    await deleteConversation("to-delete");

    expect(await getConversation("to-delete")).toBeUndefined();
    expect(await listConversations()).toHaveLength(0);
  });
});
