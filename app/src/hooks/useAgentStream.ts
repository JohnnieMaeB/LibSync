import { useCallback, useEffect, useRef, useState } from "react";
import { HttpAgent } from "@ag-ui/client";
import type { BaseEvent, RunAgentInput } from "@ag-ui/client";
import { API_BASE_URL } from "../config";
import { generateId } from "../lib/id";
import type { BotEntry, ChatEntry, NumberedWork } from "../types";

const MAX_RETRIES = 2;
const RETRY_DELAY_MS = 600;
const DEFAULT_ERROR_MSG = "⚠️ Error: Unable to reach AI service. Please try again later.";
const RATE_LIMIT_MSG = "⏳ You're sending messages a little too quickly. Please wait a moment and try again.";
const PERSIST_DEBOUNCE_MS = 300;

// Friendly, tool-specific status text shown while a tool call is in flight,
// sourced from the AG-UI TOOL_CALL_START event's toolCallName.
const TOOL_STATUS_MESSAGES: Record<string, string> = {
  search_library_policies: "📚 Checking library policies",
  search_catalog: "🔍 Searching the catalog",
  search_scholarly_works: "🎓 Looking up research",
  lookup_and_cite: "🎓 Looking up citation",
};

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

interface TurnOutcome {
  aborted: boolean;
  errorMessage: string | null;
}

// Runs one AG-UI turn to completion, retrying the *connection* (not a
// mid-stream failure) up to MAX_RETRIES times on a network error or 5xx,
// mirroring client/src/script.js's fetchWithRetry. @ag-ui/client's HttpAgent
// throws an Error with `.status` set to the HTTP status code for non-2xx
// responses (see runHttpRequest in @ag-ui/client), which is what lets this
// tell a retryable connection failure apart from a fatal one.
function runAgentOnce(
  agent: HttpAgent,
  input: RunAgentInput,
  onEvent: (event: BaseEvent) => void,
): Promise<{ outcome: "ok" | "aborted" | "rate-limited" | "retryable" | "fatal"; error?: unknown }> {
  return new Promise((resolve) => {
    let receivedAnyEvent = false;
    const subscription = agent.run(input).subscribe({
      next: (event: BaseEvent) => {
        receivedAnyEvent = true;
        onEvent(event);
      },
      error: (err: unknown) => {
        const anyErr = err as { name?: string; status?: number } | undefined;
        if (anyErr?.name === "AbortError") {
          resolve({ outcome: "aborted" });
          return;
        }
        if (!receivedAnyEvent) {
          if (anyErr?.status === 429) {
            resolve({ outcome: "rate-limited" });
            return;
          }
          if (!anyErr?.status || anyErr.status >= 500) {
            resolve({ outcome: "retryable", error: err });
            return;
          }
        }
        resolve({ outcome: "fatal", error: err });
      },
      complete: () => resolve({ outcome: "ok" }),
    });
    // Allow the caller to cancel this attempt via agent.abortRun(); nothing
    // else to do here since the Observable's error callback handles cleanup.
    void subscription;
  });
}

// Reconstructs the AG-UI wire messages the model should see from this
// conversation's rendered entries — user text as-is, and only the *text*
// blocks of each bot reply (card blocks were CUSTOM events, never part of
// the assistant's text-message content, so they're correctly left out).
function entriesToMessages(entries: ChatEntry[]): { id: string; role: string; content: string }[] {
  const messages: { id: string; role: string; content: string }[] = [];
  for (const entry of entries) {
    if (entry.kind === "user") {
      messages.push({ id: entry.id, role: "user", content: entry.text });
    } else {
      const text = entry.blocks
        .filter((b) => b.type === "text")
        .map((b) => (b as { text: string }).text)
        .join("\n\n");
      if (text) messages.push({ id: entry.id, role: "assistant", content: text });
    }
  }
  return messages;
}

export function useAgentStream({
  conversationId,
  initialEntries,
  onEntriesChange,
}: {
  conversationId: string;
  initialEntries: ChatEntry[];
  onEntriesChange: (conversationId: string, entries: ChatEntry[]) => void;
}) {
  const [entries, setEntriesState] = useState<ChatEntry[]>(initialEntries);
  const [isStreaming, setIsStreaming] = useState(false);
  const entriesRef = useRef<ChatEntry[]>(initialEntries);
  const lastQuestionRef = useRef("");
  const agentRef = useRef<HttpAgent | null>(null);
  const persistTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // entries live in a ref (not just state) so a turn can synchronously read
  // "everything sent/received so far" the moment it starts, without racing
  // React's deferred state updates — see Phase 21's history reconstruction.
  const commitEntries = useCallback(
    (next: ChatEntry[]) => {
      entriesRef.current = next;
      setEntriesState(next);
      if (persistTimerRef.current) clearTimeout(persistTimerRef.current);
      persistTimerRef.current = setTimeout(() => {
        persistTimerRef.current = null;
        onEntriesChange(conversationId, entriesRef.current);
      }, PERSIST_DEBOUNCE_MS);
    },
    [conversationId, onEntriesChange],
  );

  // Flush any pending debounced persist on unmount (e.g. the user switches
  // conversations mid-stream) so the last few streamed chunks aren't lost.
  useEffect(() => {
    return () => {
      if (persistTimerRef.current) {
        clearTimeout(persistTimerRef.current);
        onEntriesChange(conversationId, entriesRef.current);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const patchBot = useCallback(
    (id: string, updater: (entry: BotEntry) => BotEntry) => {
      commitEntries(entriesRef.current.map((e) => (e.kind === "bot" && e.id === id ? updater(e) : e)));
    },
    [commitEntries],
  );

  const removeEntry = useCallback(
    (id: string) => {
      commitEntries(entriesRef.current.filter((e) => e.id !== id));
    },
    [commitEntries],
  );

  const runTurn = useCallback(
    async (question: string) => {
      lastQuestionRef.current = question;
      // Snapshot before the bot placeholder is appended: this is exactly
      // the history the model should see for this turn (already includes
      // the latest user question, appended by sendMessage/regenerate below).
      const historyForRequest = entriesRef.current;
      const botId = generateId();
      commitEntries([
        ...entriesRef.current,
        { kind: "bot", id: botId, status: "loading", blocks: [], cardCount: 0, isLatest: false },
      ]);
      setIsStreaming(true);

      let hasContent = false;
      let cardCount = 0;
      let activeTextMessageId: string | null = null;
      let activeTextKey: string | null = null;
      let currentText = "";
      let runErrorMessage: string | null = null;

      const ensureContentStarted = () => {
        if (!hasContent) {
          hasContent = true;
          patchBot(botId, (e) => ({ ...e, status: "streaming" }));
        }
      };

      const onEvent = (event: BaseEvent) => {
        const anyEvent = event as unknown as Record<string, any>;
        switch (event.type) {
          case "TEXT_MESSAGE_START":
            activeTextMessageId = anyEvent.messageId;
            activeTextKey = null;
            currentText = "";
            return;
          case "TEXT_MESSAGE_CONTENT": {
            if (anyEvent.messageId !== activeTextMessageId) {
              activeTextMessageId = anyEvent.messageId;
              currentText = "";
              activeTextKey = null;
            }
            currentText += anyEvent.delta;
            ensureContentStarted();
            if (!activeTextKey) {
              activeTextKey = generateId();
              const key = activeTextKey;
              patchBot(botId, (e) => ({ ...e, blocks: [...e.blocks, { type: "text", key, text: currentText }] }));
            } else {
              const key = activeTextKey;
              patchBot(botId, (e) => ({
                ...e,
                blocks: e.blocks.map((b) => (b.key === key ? { ...b, text: currentText } : b)),
              }));
            }
            return;
          }
          case "TOOL_CALL_START":
            if (!hasContent) {
              const label = TOOL_STATUS_MESSAGES[anyEvent.toolCallName] || "Working";
              patchBot(botId, (e) => ({ ...e, status: "tool", toolLabel: label }));
            }
            return;
          case "CUSTOM": {
            ensureContentStarted();
            const name = anyEvent.name;
            const value = anyEvent.value || {};
            if (name === "book_card") {
              cardCount += 1;
              const number = cardCount;
              const key = generateId();
              patchBot(botId, (e) => ({
                ...e,
                cardCount: number,
                blocks: [
                  ...e.blocks,
                  {
                    type: "book",
                    key,
                    number,
                    data: {
                      title: value.title,
                      author: value.author,
                      year: value.first_publish_year,
                      availability: value.availability,
                      coverUrl: value.cover_url,
                      url: value.url,
                    },
                  },
                ],
              }));
            } else if (name === "research_results") {
              const works: NumberedWork[] = (value.works || []).map((work: Record<string, any>) => {
                cardCount += 1;
                return {
                  number: cardCount,
                  data: {
                    title: work.title,
                    authors: work.authors,
                    year: work.year,
                    doi: work.doi,
                    citationCount: work.citation_count,
                    isOa: Boolean(work.is_oa),
                    abstract: work.abstract,
                  },
                };
              });
              const finalCount = cardCount;
              const key = generateId();
              patchBot(botId, (e) => ({
                ...e,
                cardCount: finalCount,
                blocks: [...e.blocks, { type: "research", key, intro: value.intro, works }],
              }));
            } else if (name === "citation") {
              cardCount += 1;
              const number = cardCount;
              const key = generateId();
              patchBot(botId, (e) => ({
                ...e,
                cardCount: number,
                blocks: [
                  ...e.blocks,
                  {
                    type: "citation",
                    key,
                    number,
                    data: {
                      formatted: value.formatted,
                      doi: value.doi,
                      style: value.style,
                      availableStyles: value.available_styles,
                    },
                  },
                ],
              }));
            }
            return;
          }
          case "RUN_ERROR":
            runErrorMessage = anyEvent.message || DEFAULT_ERROR_MSG;
            return;
          default:
            return;
        }
      };

      const input: RunAgentInput = {
        threadId: conversationId,
        runId: generateId(),
        state: null,
        messages: entriesToMessages(historyForRequest),
        tools: [],
        context: [],
        forwardedProps: null,
      } as RunAgentInput;

      const outcome: TurnOutcome = { aborted: false, errorMessage: null };

      for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
        const agent = new HttpAgent({ url: `${API_BASE_URL}/agent`, threadId: input.threadId });
        agentRef.current = agent;
        const result = await runAgentOnce(agent, input, onEvent);

        if (result.outcome === "ok") {
          // A RUN_ERROR event (a graceful in-band error, as opposed to a
          // connection failure) still lets the stream complete normally —
          // it just means the turn ended in an error state, not success.
          if (runErrorMessage) outcome.errorMessage = runErrorMessage;
          break;
        }
        if (result.outcome === "aborted") {
          outcome.aborted = true;
          break;
        }
        if (result.outcome === "rate-limited") {
          outcome.errorMessage = RATE_LIMIT_MSG;
          break;
        }
        if (result.outcome === "retryable" && attempt < MAX_RETRIES) {
          await sleep(RETRY_DELAY_MS * (attempt + 1));
          continue;
        }
        outcome.errorMessage = DEFAULT_ERROR_MSG;
        if (result.error) console.error(result.error);
        break;
      }

      agentRef.current = null;

      if (outcome.aborted) {
        const demoted = entriesRef.current.map((e) => (e.kind === "bot" ? { ...e, isLatest: false } : e));
        commitEntries(
          demoted.map((e) => (e.kind === "bot" && e.id === botId ? { ...e, status: "stopped", isLatest: true } : e)),
        );
      } else if (outcome.errorMessage) {
        patchBot(botId, (e) => ({ ...e, status: "error", errorText: outcome.errorMessage! }));
      } else {
        const demoted = entriesRef.current.map((e) => (e.kind === "bot" ? { ...e, isLatest: false } : e));
        commitEntries(
          demoted.map((e) => (e.kind === "bot" && e.id === botId ? { ...e, status: "done", isLatest: true } : e)),
        );
      }

      setIsStreaming(false);
    },
    [commitEntries, conversationId, patchBot],
  );

  const sendMessage = useCallback(
    (question: string) => {
      const trimmed = question.trim();
      if (!trimmed) return;
      commitEntries([...entriesRef.current, { kind: "user", id: generateId(), text: trimmed }]);
      void runTurn(trimmed);
    },
    [commitEntries, runTurn],
  );

  const regenerate = useCallback(
    (entryId: string) => {
      if (!lastQuestionRef.current) return;
      removeEntry(entryId);
      void runTurn(lastQuestionRef.current);
    },
    [removeEntry, runTurn],
  );

  const stop = useCallback(() => {
    agentRef.current?.abortRun();
  }, []);

  return { entries, isStreaming, sendMessage, regenerate, retry: regenerate, stop };
}
