import { useCallback, useEffect, useState } from "react";
import { deleteConversation, getConversation, listConversations, putConversation } from "../lib/db";
import { generateId } from "../lib/id";
import type { ChatEntry, Conversation, ConversationSummary } from "../types";

const TITLE_MAX_LENGTH = 40;

function titleFromFirstMessage(text: string): string {
  const trimmed = text.trim();
  if (trimmed.length <= TITLE_MAX_LENGTH) return trimmed;
  return `${trimmed.slice(0, TITLE_MAX_LENGTH).trimEnd()}…`;
}

function toSummary(conversation: Conversation): ConversationSummary {
  return { id: conversation.id, title: conversation.title, updatedAt: conversation.updatedAt };
}

export function useConversations() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  // Every mount starts on a fresh, not-yet-persisted conversation (matching
  // ChatGPT/Claude's "new chat by default" behavior) — past conversations
  // are still loaded into the sidebar below and remain one click away.
  const [activeId, setActiveId] = useState<string>(() => generateId());
  const [activeEntries, setActiveEntries] = useState<ChatEntry[]>([]);

  useEffect(() => {
    void (async () => {
      const list = await listConversations();
      setConversations(list.map(toSummary));
    })();
  }, []);

  const createConversation = useCallback(() => {
    const id = generateId();
    setActiveId(id);
    setActiveEntries([]);
    return id;
  }, []);

  const selectConversation = useCallback(async (id: string) => {
    const conversation = await getConversation(id);
    setActiveId(id);
    setActiveEntries(conversation?.entries ?? []);
  }, []);

  const renameConversation = useCallback(async (id: string, title: string) => {
    const conversation = await getConversation(id);
    if (!conversation) return;
    const updated = { ...conversation, title };
    await putConversation(updated);
    setConversations((prev) => prev.map((c) => (c.id === id ? toSummary(updated) : c)));
  }, []);

  const removeConversation = useCallback(
    async (id: string) => {
      await deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (activeId === id) {
        setActiveId(generateId());
        setActiveEntries([]);
      }
    },
    [activeId],
  );

  // Called by the conversation-scoped chat stream whenever its entries
  // change, so the sidebar list and IndexedDB both stay in sync with
  // whichever conversation is currently active.
  const persistActiveEntries = useCallback(async (id: string, entries: ChatEntry[]) => {
    if (entries.length === 0) return;
    const firstUserEntry = entries.find((e) => e.kind === "user");
    const existing = await getConversation(id);
    const now = Date.now();
    const conversation: Conversation = {
      id,
      title: existing?.title ?? (firstUserEntry ? titleFromFirstMessage(firstUserEntry.text) : "New chat"),
      createdAt: existing?.createdAt ?? now,
      updatedAt: now,
      entries,
    };
    await putConversation(conversation);
    setConversations((prev) => {
      const withoutThis = prev.filter((c) => c.id !== id);
      return [toSummary(conversation), ...withoutThis].sort((a, b) => b.updatedAt - a.updatedAt);
    });
  }, []);

  return {
    conversations,
    activeId,
    activeEntries,
    createConversation,
    selectConversation,
    renameConversation,
    removeConversation,
    persistActiveEntries,
  };
}
