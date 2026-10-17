import { describe, expect, it, vi } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";
import { useConversations, type ConversationSync } from "./useConversations";
import { getConversation, putConversation } from "../lib/db";
import type { ChatEntry, Conversation } from "../types";

function remote(id: string, updatedAt: number, title = "Remote"): Conversation {
  return { id, title, createdAt: 1, updatedAt, entries: [{ kind: "user", id: `${id}-u`, text: title }] };
}

function fakeSync(pulled: Conversation[] = []): ConversationSync & { pushed: Conversation[]; removed: string[] } {
  const pushed: Conversation[] = [];
  const removed: string[] = [];
  return {
    pushed,
    removed,
    pull: vi.fn(async () => pulled),
    push: vi.fn(async (c: Conversation) => void pushed.push(c)),
    remove: vi.fn(async (id: string) => void removed.push(id)),
  };
}

describe("useConversations sync (Tier 9 Phase 37)", () => {
  it("pulls a signed-in patron's conversations onto the device, newer copy winning", async () => {
    await putConversation(remote("sync-old", 10, "Local newer"));
    const sync = fakeSync([remote("sync-new", 50, "From account"), remote("sync-old", 5, "Account older")]);
    const { result } = renderHook(() => useConversations(sync));

    await waitFor(() => expect(result.current.conversations.some((c) => c.id === "sync-new")).toBe(true));
    expect((await getConversation("sync-new"))?.title).toBe("From account");
    expect((await getConversation("sync-old"))?.title).toBe("Local newer");
  });

  it("pushes saved conversations and deletions", async () => {
    const sync = fakeSync();
    const { result } = renderHook(() => useConversations(sync));
    const entries: ChatEntry[] = [{ kind: "user", id: "u", text: "Do you have hotspots?" }];

    await act(() => result.current.persistActiveEntries("sync-push", entries));
    expect(sync.pushed.map((c) => c.id)).toEqual(["sync-push"]);
    await act(() => result.current.removeConversation("sync-push"));
    expect(sync.removed).toEqual(["sync-push"]);
  });

  it("keeps working on-device when sync fails", async () => {
    const sync: ConversationSync = {
      pull: vi.fn(async () => {
        throw new Error("offline");
      }),
      push: vi.fn(async () => {
        throw new Error("offline");
      }),
      remove: vi.fn(async () => {}),
    };
    const { result } = renderHook(() => useConversations(sync));
    await act(() => result.current.persistActiveEntries("sync-offline", [{ kind: "user", id: "u", text: "hi" }]));
    expect(await getConversation("sync-offline")).toBeDefined();
  });

  it("never syncs without a signed-in patron", async () => {
    const { result } = renderHook(() => useConversations(null));
    await act(() => result.current.persistActiveEntries("sync-anon", [{ kind: "user", id: "u", text: "hi" }]));
    expect(await getConversation("sync-anon")).toBeDefined();
  });
});
