import { useCallback, useRef, useState } from "react";
import { HttpAgent } from "@ag-ui/client";
import type { BaseEvent, RunAgentInput } from "@ag-ui/client";
import { API_BASE_URL } from "../config";
import { generateId, getOrCreateSessionId } from "../lib/session";
import type { BotEntry, ChatEntry, NumberedWork } from "../types";

const MAX_RETRIES = 2;
const RETRY_DELAY_MS = 600;
const DEFAULT_ERROR_MSG = "⚠️ Error: Unable to reach AI service. Please try again later.";
const RATE_LIMIT_MSG = "⏳ You're sending messages a little too quickly. Please wait a moment and try again.";

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

export function useAgentStream() {
  const [entries, setEntries] = useState<ChatEntry[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const lastQuestionRef = useRef("");
  const agentRef = useRef<HttpAgent | null>(null);

  const patchBot = useCallback((id: string, updater: (entry: BotEntry) => BotEntry) => {
    setEntries((prev) =>
      prev.map((e) => (e.kind === "bot" && e.id === id ? updater(e) : e)),
    );
  }, []);

  const removeEntry = useCallback((id: string) => {
    setEntries((prev) => prev.filter((e) => e.id !== id));
  }, []);

  const runTurn = useCallback(
    async (question: string) => {
      lastQuestionRef.current = question;
      const botId = generateId();
      setEntries((prev) => [
        ...prev,
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
        threadId: getOrCreateSessionId(),
        runId: generateId(),
        state: null,
        messages: [{ id: generateId(), role: "user", content: question }],
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
        setEntries((prev) => {
          const demoted = prev.map((e) => (e.kind === "bot" ? { ...e, isLatest: false } : e));
          return demoted.map((e) => {
            if (e.kind !== "bot" || e.id !== botId) return e;
            return { ...e, status: "stopped", isLatest: true };
          });
        });
      } else if (outcome.errorMessage) {
        patchBot(botId, (e) => ({ ...e, status: "error", errorText: outcome.errorMessage! }));
      } else {
        setEntries((prev) => {
          const demoted = prev.map((e) => (e.kind === "bot" ? { ...e, isLatest: false } : e));
          return demoted.map((e) => {
            if (e.kind !== "bot" || e.id !== botId) return e;
            return { ...e, status: "done", isLatest: true };
          });
        });
      }

      setIsStreaming(false);
    },
    [patchBot],
  );

  const sendMessage = useCallback(
    (question: string) => {
      const trimmed = question.trim();
      if (!trimmed) return;
      setEntries((prev) => [...prev, { kind: "user", id: generateId(), text: trimmed }]);
      void runTurn(trimmed);
    },
    [runTurn],
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
