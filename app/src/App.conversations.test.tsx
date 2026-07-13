import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";
import { deleteConversation, listConversations } from "./lib/db";

// Builds one AG-UI SSE event chunk, matching the wire format encoded by
// pydantic_ai's AGUIEventStream: a single `data: {...}` line per event.
function aguiEvent(payload: Record<string, unknown>) {
  return `data: ${JSON.stringify(payload)}\n\n`;
}

function makeStreamingResponse(chunks: string[], { status = 200, ok = true } = {}) {
  let index = 0;
  const encoder = new TextEncoder();
  return {
    ok,
    status,
    headers: { get: () => "text/event-stream" },
    body: {
      getReader() {
        return {
          async read() {
            if (index >= chunks.length) return { done: true, value: undefined };
            const value = encoder.encode(chunks[index]);
            index += 1;
            return { done: false, value };
          },
        };
      },
    },
  };
}

function textMessageEvents(messageId: string, texts: string[]) {
  const events = [aguiEvent({ type: "TEXT_MESSAGE_START", messageId, role: "assistant" })];
  for (const text of texts) events.push(aguiEvent({ type: "TEXT_MESSAGE_CONTENT", messageId, delta: text }));
  events.push(aguiEvent({ type: "TEXT_MESSAGE_END", messageId }));
  return events;
}

async function sendViaTextarea(user: ReturnType<typeof userEvent.setup>, text: string) {
  const textarea = screen.getByLabelText("Type your question");
  await user.type(textarea, text);
  await user.click(screen.getByRole("button", { name: /send message/i }));
}

// The debounced IndexedDB persist (300ms, see useAgentStream's
// PERSIST_DEBOUNCE_MS) needs real time to elapse to flush; these tests use
// real timers, so a small real wait is needed after a turn completes.
async function waitForPersist() {
  await act(() => new Promise((resolve) => setTimeout(resolve, 400)));
}

describe("Multi-conversation history (Tier 5)", () => {
  beforeEach(async () => {
    vi.stubGlobal("fetch", vi.fn());
    const existing = await listConversations();
    await Promise.all(existing.map((c) => deleteConversation(c.id)));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("creates a new, separate conversation when New chat is clicked, and switching back preserves the first one", async () => {
    (fetch as any).mockResolvedValueOnce(
      makeStreamingResponse([
        aguiEvent({ type: "RUN_STARTED", threadId: "t1", runId: "r1" }),
        ...textMessageEvents("m1", ["First reply"]),
        aguiEvent({ type: "RUN_FINISHED", threadId: "t1", runId: "r1" }),
      ]),
    );

    const user = userEvent.setup();
    render(<App />);
    await sendViaTextarea(user, "First conversation question");
    await screen.findByText("First reply");
    await waitForPersist();

    // Start a new chat — the sidebar should now list the first conversation
    // (titled from its first message) and the composer/log should be empty.
    await user.click(screen.getByRole("button", { name: "New chat" }));
    expect(screen.queryByText("First reply")).toBeNull();

    const nav = screen.getByRole("navigation", { name: "Conversations" });
    const firstConversationLink = await within(nav).findByRole("button", {
      name: "First conversation question",
    });

    await user.click(firstConversationLink);
    await screen.findByText("First reply");
  });

  it("persists a conversation's messages across a simulated reload (re-render)", async () => {
    (fetch as any).mockResolvedValueOnce(
      makeStreamingResponse([
        aguiEvent({ type: "RUN_STARTED", threadId: "t1", runId: "r1" }),
        ...textMessageEvents("m1", ["Persisted reply"]),
        aguiEvent({ type: "RUN_FINISHED", threadId: "t1", runId: "r1" }),
      ]),
    );

    const user = userEvent.setup();
    const { unmount } = render(<App />);
    await sendViaTextarea(user, "Reload test question");
    await screen.findByText("Persisted reply");
    await waitForPersist();
    unmount();

    render(<App />);
    const nav = screen.getByRole("navigation", { name: "Conversations" });
    const conversationLink = await within(nav).findByRole("button", { name: "Reload test question" });
    await user.click(conversationLink);

    await screen.findByText("Persisted reply");
  });

  it("renames a conversation from the sidebar", async () => {
    (fetch as any).mockResolvedValueOnce(
      makeStreamingResponse([
        aguiEvent({ type: "RUN_STARTED", threadId: "t1", runId: "r1" }),
        ...textMessageEvents("m1", ["reply"]),
        aguiEvent({ type: "RUN_FINISHED", threadId: "t1", runId: "r1" }),
      ]),
    );

    const user = userEvent.setup();
    render(<App />);
    await sendViaTextarea(user, "Renamable question");
    await screen.findByText("reply");
    await waitForPersist();

    const nav = screen.getByRole("navigation", { name: "Conversations" });
    const title = await within(nav).findByRole("button", { name: "Renamable question" });
    await user.dblClick(title);

    const input = within(nav).getByRole("textbox", { name: "Conversation title" });
    await user.clear(input);
    await user.type(input, "My renamed chat{Enter}");

    await within(nav).findByRole("button", { name: "My renamed chat" });
  });

  it("deletes a conversation from the sidebar after confirming", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    (fetch as any).mockResolvedValueOnce(
      makeStreamingResponse([
        aguiEvent({ type: "RUN_STARTED", threadId: "t1", runId: "r1" }),
        ...textMessageEvents("m1", ["reply"]),
        aguiEvent({ type: "RUN_FINISHED", threadId: "t1", runId: "r1" }),
      ]),
    );

    const user = userEvent.setup();
    render(<App />);
    await sendViaTextarea(user, "Deletable question");
    await screen.findByText("reply");
    await waitForPersist();

    const nav = screen.getByRole("navigation", { name: "Conversations" });
    await within(nav).findByRole("button", { name: "Deletable question" });
    await user.click(within(nav).getByRole("button", { name: "Delete Deletable question" }));

    await waitFor(() => {
      expect(within(nav).queryByRole("button", { name: "Deletable question" })).toBeNull();
    });
  });
});
