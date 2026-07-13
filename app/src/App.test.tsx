import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";
import { API_BASE_URL } from "./config";
import { deleteConversation, listConversations } from "./lib/db";

// Builds one AG-UI SSE event chunk, matching the wire format encoded by
// pydantic_ai's AGUIEventStream: a single `data: {...}` line per event.
function aguiEvent(payload: Record<string, unknown>) {
  return `data: ${JSON.stringify(payload)}\n\n`;
}

// Builds a fetch Response-like object whose body streams the given SSE
// event strings one chunk per reader.read() call, mirroring how the real
// StreamingResponse endpoint (POST /agent) delivers server-sent events.
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
            if (index >= chunks.length) {
              return { done: true, value: undefined };
            }
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
  for (const text of texts) {
    events.push(aguiEvent({ type: "TEXT_MESSAGE_CONTENT", messageId, delta: text }));
  }
  events.push(aguiEvent({ type: "TEXT_MESSAGE_END", messageId }));
  return events;
}

async function sendViaTextarea(user: ReturnType<typeof userEvent.setup>, text: string) {
  const textarea = screen.getByLabelText("Type your question");
  await user.type(textarea, text);
  await user.click(screen.getByRole("button", { name: /send message/i }));
}

function getBotBubbles() {
  return document.querySelectorAll("#chatBox .bot:not(.intro)");
}

describe("LibSync chat", () => {
  beforeEach(async () => {
    vi.stubGlobal("fetch", vi.fn());
    localStorage.clear();
    // Conversations persist to IndexedDB across tests within this file
    // (fake-indexeddb isn't reset per-test); clear them so each test starts
    // from a clean slate regardless of what earlier tests in this file saved.
    const existing = await listConversations();
    await Promise.all(existing.map((c) => deleteConversation(c.id)));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it("does not send a message if the input is empty", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: /send message/i }));
    expect(fetch).not.toHaveBeenCalled();
  });

  it("posts an AG-UI RunAgentInput to /agent with a threadId and the new user turn", async () => {
    (fetch as any).mockResolvedValueOnce(
      makeStreamingResponse([
        aguiEvent({ type: "RUN_STARTED", threadId: "abc-123", runId: "run-1" }),
        ...textMessageEvents("msg-1", ["Test", " reply"]),
        aguiEvent({ type: "RUN_FINISHED", threadId: "abc-123", runId: "run-1" }),
      ]),
    );

    const user = userEvent.setup();
    render(<App />);
    await sendViaTextarea(user, "Test message");

    await screen.findByText("Test reply");

    expect(fetch).toHaveBeenCalledTimes(1);
    const [url, options] = (fetch as any).mock.calls[0];
    expect(url).toBe(`${API_BASE_URL}/agent`);
    const body = JSON.parse(options.body);
    expect(typeof body.threadId).toBe("string");
    expect(body.messages).toHaveLength(1);
    expect(body.messages[0]).toMatchObject({ role: "user", content: "Test message" });
  });

  it("reuses the same threadId across requests", async () => {
    (fetch as any).mockImplementation(async () =>
      makeStreamingResponse([
        aguiEvent({ type: "RUN_STARTED", threadId: "abc-123", runId: "run-1" }),
        ...textMessageEvents("msg-1", ["ok"]),
        aguiEvent({ type: "RUN_FINISHED", threadId: "abc-123", runId: "run-1" }),
      ]),
    );

    const user = userEvent.setup();
    render(<App />);
    await sendViaTextarea(user, "first");
    await screen.findByText("ok");
    await sendViaTextarea(user, "second");
    await screen.findAllByText("ok");

    const firstBody = JSON.parse((fetch as any).mock.calls[0][1].body);
    const secondBody = JSON.parse((fetch as any).mock.calls[1][1].body);
    expect(secondBody.threadId).toBe(firstBody.threadId);
  });

  it("sends the whole conversation's history (not just the latest question) on the second turn", async () => {
    // Tier 5: the server stops relying on its own cross-request memory once
    // the client reliably resends full history — see server/app/routers/agent.py.
    (fetch as any).mockImplementation(async () =>
      makeStreamingResponse([
        aguiEvent({ type: "RUN_STARTED", threadId: "abc-123", runId: "run-1" }),
        ...textMessageEvents("msg-1", ["first reply"]),
        aguiEvent({ type: "RUN_FINISHED", threadId: "abc-123", runId: "run-1" }),
      ]),
    );

    const user = userEvent.setup();
    render(<App />);
    await sendViaTextarea(user, "first question");
    await screen.findByText("first reply");
    await sendViaTextarea(user, "second question");
    await screen.findAllByText("first reply");

    const secondBody = JSON.parse((fetch as any).mock.calls[1][1].body);
    expect(secondBody.messages).toHaveLength(3);
    expect(secondBody.messages[0]).toMatchObject({ role: "user", content: "first question" });
    expect(secondBody.messages[1]).toMatchObject({ role: "assistant", content: "first reply" });
    expect(secondBody.messages[2]).toMatchObject({ role: "user", content: "second question" });
  });

  it("renders a book_card CUSTOM event as a real card with cover and link-out", async () => {
    (fetch as any).mockResolvedValueOnce(
      makeStreamingResponse([
        aguiEvent({ type: "RUN_STARTED", threadId: "abc-123", runId: "run-1" }),
        aguiEvent({
          type: "CUSTOM",
          name: "book_card",
          value: {
            title: "Project Hail Mary",
            author: "Andy Weir",
            first_publish_year: 2021,
            availability: "lendable",
            cover_url: "https://covers.openlibrary.org/b/id/12345-M.jpg",
            url: "https://openlibrary.org/works/OL123W",
          },
        }),
        aguiEvent({ type: "RUN_FINISHED", threadId: "abc-123", runId: "run-1" }),
      ]),
    );

    const user = userEvent.setup();
    render(<App />);
    await sendViaTextarea(user, "Is Project Hail Mary available?");

    const titleLink = await screen.findByRole("link", { name: "Project Hail Mary (2021)" });
    expect(titleLink).toHaveAttribute("href", "https://openlibrary.org/works/OL123W");
    expect(screen.getByText("lendable")).toBeInTheDocument();
    const cover = document.querySelector(".book-card-cover") as HTMLImageElement;
    expect(cover.src).toBe("https://covers.openlibrary.org/b/id/12345-M.jpg");
  });

  it("renders multiple book_card CUSTOM events from one tool call as separate cards", async () => {
    (fetch as any).mockResolvedValueOnce(
      makeStreamingResponse([
        aguiEvent({ type: "RUN_STARTED", threadId: "abc-123", runId: "run-1" }),
        aguiEvent({
          type: "CUSTOM",
          name: "book_card",
          value: { title: "Project Hail Mary", author: "Andy Weir", first_publish_year: 2021, availability: "lendable" },
        }),
        aguiEvent({
          type: "CUSTOM",
          name: "book_card",
          value: { title: "The Martian", author: "Andy Weir", first_publish_year: 2011, availability: "checked out" },
        }),
        aguiEvent({ type: "RUN_FINISHED", threadId: "abc-123", runId: "run-1" }),
      ]),
    );

    const user = userEvent.setup();
    render(<App />);
    await sendViaTextarea(user, "Any Andy Weir books?");

    await screen.findByText("Project Hail Mary (2021)");
    expect(document.querySelectorAll(".book-card")).toHaveLength(2);
    expect(screen.getByText("The Martian (2011)")).toBeInTheDocument();
  });

  it("keeps a card visible when narration text streams in after it (not before)", async () => {
    (fetch as any).mockResolvedValueOnce(
      makeStreamingResponse([
        aguiEvent({ type: "RUN_STARTED", threadId: "abc-123", runId: "run-1" }),
        aguiEvent({
          type: "CUSTOM",
          name: "book_card",
          value: { title: "Project Hail Mary", author: "Andy Weir", first_publish_year: 2021, availability: "lendable" },
        }),
        ...textMessageEvents("msg-1", ["I found it in our catalog!"]),
        aguiEvent({ type: "RUN_FINISHED", threadId: "abc-123", runId: "run-1" }),
      ]),
    );

    const user = userEvent.setup();
    render(<App />);
    await sendViaTextarea(user, "Is Project Hail Mary available?");

    await screen.findByText("I found it in our catalog!");
    expect(screen.getByText("Project Hail Mary (2021)")).toBeInTheDocument();
  });

  it("renders a research_results CUSTOM event as a result-list card", async () => {
    (fetch as any).mockResolvedValueOnce(
      makeStreamingResponse([
        aguiEvent({ type: "RUN_STARTED", threadId: "abc-123", runId: "run-1" }),
        aguiEvent({
          type: "CUSTOM",
          name: "research_results",
          value: {
            intro: 'Found 1 work(s) for "large language models":',
            works: [
              {
                title: "ChatGPT for good?",
                authors: "Enkelejda Kasneci",
                year: 2023,
                citation_count: 5340,
                is_oa: true,
                doi: "https://doi.org/10.1016/j.lindif.2023.102274",
                abstract: "Large language models help.",
              },
            ],
          },
        }),
        aguiEvent({ type: "RUN_FINISHED", threadId: "abc-123", runId: "run-1" }),
      ]),
    );

    const user = userEvent.setup();
    render(<App />);
    await sendViaTextarea(user, "Find recent papers on large language models");

    expect(await screen.findByText('Found 1 work(s) for "large language models":')).toBeInTheDocument();
    const titleLink = screen.getByRole("link", { name: "ChatGPT for good? (2023)" });
    expect(titleLink).toHaveAttribute("href", "https://doi.org/10.1016/j.lindif.2023.102274");
    expect(screen.getByText("Enkelejda Kasneci")).toBeInTheDocument();
    expect(screen.getByText("5340 citations")).toBeInTheDocument();
    expect(screen.getByText("Open access")).toBeInTheDocument();
    await user.click(screen.getByText("Abstract"));
    expect(screen.getByText("Large language models help.")).toBeInTheDocument();
  });

  it("renders a citation CUSTOM event as a citation card with copy and style controls, and switches style live", async () => {
    (fetch as any).mockResolvedValueOnce(
      makeStreamingResponse([
        aguiEvent({ type: "RUN_STARTED", threadId: "abc-123", runId: "run-1" }),
        aguiEvent({
          type: "CUSTOM",
          name: "citation",
          value: {
            formatted: "Kasneci, E. (2023). ChatGPT for good?",
            style: "apa",
            doi: "10.1016/j.lindif.2023.102274",
            available_styles: ["apa", "chicago", "mla"],
          },
        }),
        aguiEvent({ type: "RUN_FINISHED", threadId: "abc-123", runId: "run-1" }),
      ]),
    );

    const user = userEvent.setup();
    render(<App />);
    await sendViaTextarea(user, "Cite this in APA: 10.1016/j.lindif.2023.102274");

    expect(await screen.findByText("Kasneci, E. (2023). ChatGPT for good?")).toBeInTheDocument();
    const select = screen.getByRole("combobox") as HTMLSelectElement;
    expect(Array.from(select.options).map((o) => o.value)).toEqual(["apa", "chicago", "mla"]);

    (fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ formatted: "Kasneci, E. “ChatGPT for Good?”", style: "mla" }),
    });
    await user.selectOptions(select, "mla");

    await screen.findByText("Kasneci, E. “ChatGPT for Good?”");
    expect(fetch).toHaveBeenLastCalledWith(`${API_BASE_URL}/citation/10.1016/j.lindif.2023.102274?style=mla`);
  });

  it("shows the RUN_ERROR message with a distinct error style and a Retry button", async () => {
    (fetch as any).mockResolvedValueOnce(
      makeStreamingResponse([
        aguiEvent({ type: "RUN_STARTED", threadId: "abc-123", runId: "run-1" }),
        aguiEvent({ type: "RUN_ERROR", message: "boom" }),
      ]),
    );

    const user = userEvent.setup();
    render(<App />);
    await sendViaTextarea(user, "Trigger failure");

    await screen.findByText("boom");
    const bots = getBotBubbles();
    expect(bots).toHaveLength(1);
    expect(bots[0].classList.contains("error")).toBe(true);
    expect(within(bots[0] as HTMLElement).getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("shows a fallback message when the run finishes with no text or cards", async () => {
    (fetch as any).mockResolvedValueOnce(
      makeStreamingResponse([
        aguiEvent({ type: "RUN_STARTED", threadId: "abc-123", runId: "run-1" }),
        aguiEvent({ type: "RUN_FINISHED", threadId: "abc-123", runId: "run-1" }),
      ]),
    );

    const user = userEvent.setup();
    render(<App />);
    await sendViaTextarea(user, "Hmm");

    await screen.findByText("Sorry, I couldn’t find an answer right now.");
  });

  it("shows a distinct message when rate limited", async () => {
    (fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 429,
      headers: { get: () => "application/json" },
      text: async () => JSON.stringify({ detail: "Too many requests" }),
    });

    const user = userEvent.setup();
    render(<App />);
    await sendViaTextarea(user, "Another message");

    await screen.findByText(/too quickly/i);
  });

  it("retries on network failure before giving up", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    (fetch as any)
      .mockRejectedValueOnce(new Error("network down"))
      .mockRejectedValueOnce(new Error("network down"))
      .mockRejectedValueOnce(new Error("network down"));

    const user = userEvent.setup({ delay: null });
    render(<App />);
    await sendViaTextarea(user, "Another message");

    await act(async () => {
      await vi.runAllTimersAsync();
    });
    await screen.findByText("⚠️ Error: Unable to reach AI service. Please try again later.");
    expect(fetch).toHaveBeenCalledTimes(3);
  });

  it("recovers if a retry succeeds after a transient failure", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    (fetch as any).mockRejectedValueOnce(new Error("network blip")).mockResolvedValueOnce(
      makeStreamingResponse([
        aguiEvent({ type: "RUN_STARTED", threadId: "abc-123", runId: "run-1" }),
        ...textMessageEvents("msg-1", ["Recovered"]),
        aguiEvent({ type: "RUN_FINISHED", threadId: "abc-123", runId: "run-1" }),
      ]),
    );

    const user = userEvent.setup({ delay: null });
    render(<App />);
    await sendViaTextarea(user, "Another message");

    await act(async () => {
      await vi.runAllTimersAsync();
    });
    await screen.findByText("Recovered");
    expect(fetch).toHaveBeenCalledTimes(2);
  });

  it('shows a "Grounded in N sources" tag and numbered badges when cards are rendered', async () => {
    (fetch as any).mockResolvedValueOnce(
      makeStreamingResponse([
        aguiEvent({ type: "RUN_STARTED", threadId: "abc-123", runId: "run-1" }),
        aguiEvent({
          type: "CUSTOM",
          name: "book_card",
          value: { title: "Project Hail Mary", author: "Andy Weir", first_publish_year: 2021, availability: "lendable" },
        }),
        aguiEvent({
          type: "CUSTOM",
          name: "book_card",
          value: { title: "The Martian", author: "Andy Weir", first_publish_year: 2011, availability: "checked out" },
        }),
        aguiEvent({ type: "RUN_FINISHED", threadId: "abc-123", runId: "run-1" }),
      ]),
    );

    const user = userEvent.setup();
    render(<App />);
    await sendViaTextarea(user, "Any Andy Weir books?");

    await screen.findByText("Grounded in 2 sources");
    const badges = document.querySelectorAll(".source-badge");
    expect(Array.from(badges).map((b) => b.textContent)).toEqual(["1", "2"]);
  });

  it("gives a plain-text reply no grounded tag", async () => {
    (fetch as any).mockResolvedValueOnce(
      makeStreamingResponse([
        aguiEvent({ type: "RUN_STARTED", threadId: "abc-123", runId: "run-1" }),
        ...textMessageEvents("msg-1", ["Hi there!"]),
        aguiEvent({ type: "RUN_FINISHED", threadId: "abc-123", runId: "run-1" }),
      ]),
    );

    const user = userEvent.setup();
    render(<App />);
    await sendViaTextarea(user, "Hello");

    await screen.findByText("Hi there!");
    expect(document.querySelector(".grounded-tag")).toBeNull();
  });

  it("keeps a regenerate action only on the most recent bot message; copy stays on both", async () => {
    (fetch as any).mockResolvedValueOnce(
      makeStreamingResponse([
        aguiEvent({ type: "RUN_STARTED", threadId: "abc-123", runId: "run-1" }),
        ...textMessageEvents("msg-1", ["a1"]),
        aguiEvent({ type: "RUN_FINISHED", threadId: "abc-123", runId: "run-1" }),
      ]),
    );
    const user = userEvent.setup();
    render(<App />);
    await sendViaTextarea(user, "q1");
    await screen.findByText("a1");

    (fetch as any).mockResolvedValueOnce(
      makeStreamingResponse([
        aguiEvent({ type: "RUN_STARTED", threadId: "abc-123", runId: "run-2" }),
        ...textMessageEvents("msg-2", ["a2"]),
        aguiEvent({ type: "RUN_FINISHED", threadId: "abc-123", runId: "run-2" }),
      ]),
    );
    await sendViaTextarea(user, "q2");
    await screen.findByText("a2");

    const bots = getBotBubbles();
    expect(bots).toHaveLength(2);
    expect(within(bots[0] as HTMLElement).queryByRole("button", { name: /regenerate/i })).toBeNull();
    expect(within(bots[0] as HTMLElement).getByRole("button", { name: /copy message/i })).toBeInTheDocument();
    expect(within(bots[1] as HTMLElement).getByRole("button", { name: /regenerate/i })).toBeInTheDocument();
  });

  it("regenerate re-runs the last question without appending a new user bubble", async () => {
    (fetch as any).mockResolvedValueOnce(
      makeStreamingResponse([
        aguiEvent({ type: "RUN_STARTED", threadId: "abc-123", runId: "run-1" }),
        ...textMessageEvents("msg-1", ["first answer"]),
        aguiEvent({ type: "RUN_FINISHED", threadId: "abc-123", runId: "run-1" }),
      ]),
    );
    const user = userEvent.setup();
    render(<App />);
    await sendViaTextarea(user, "first question");
    await screen.findByText("first answer");

    (fetch as any).mockResolvedValueOnce(
      makeStreamingResponse([
        aguiEvent({ type: "RUN_STARTED", threadId: "abc-123", runId: "run-2" }),
        ...textMessageEvents("msg-2", ["second answer"]),
        aguiEvent({ type: "RUN_FINISHED", threadId: "abc-123", runId: "run-2" }),
      ]),
    );
    await user.click(screen.getByRole("button", { name: /regenerate/i }));

    await screen.findByText("second answer");
    expect(document.querySelectorAll("#chatBox .user")).toHaveLength(1);
    expect(getBotBubbles()).toHaveLength(1);
  });

  it("Retry resubmits the last question without duplicating the user bubble", async () => {
    (fetch as any).mockResolvedValueOnce(
      makeStreamingResponse([
        aguiEvent({ type: "RUN_STARTED", threadId: "abc-123", runId: "run-1" }),
        aguiEvent({ type: "RUN_ERROR", message: "boom" }),
      ]),
    );
    const user = userEvent.setup();
    render(<App />);
    await sendViaTextarea(user, "Trigger failure");
    await screen.findByText("boom");

    (fetch as any).mockResolvedValueOnce(
      makeStreamingResponse([
        aguiEvent({ type: "RUN_STARTED", threadId: "abc-123", runId: "run-2" }),
        ...textMessageEvents("msg-2", ["recovered reply"]),
        aguiEvent({ type: "RUN_FINISHED", threadId: "abc-123", runId: "run-2" }),
      ]),
    );
    await user.click(screen.getByRole("button", { name: "Retry" }));

    await screen.findByText("recovered reply");
    expect(document.querySelectorAll("#chatBox .user")).toHaveLength(1);
    expect(getBotBubbles()).toHaveLength(1);
  });

  it("turns the send button into Stop while streaming and reverts after completion", async () => {
    // A response that doesn't resolve until we release it, so the
    // in-flight "streaming" state is observable rather than racing a
    // same-microtask-queue mock response to completion.
    let releaseFetch!: (value: unknown) => void;
    const gatedResponse = new Promise((resolve) => {
      releaseFetch = resolve;
    });
    (fetch as any).mockImplementationOnce(() => gatedResponse);

    const user = userEvent.setup();
    render(<App />);
    const textarea = screen.getByLabelText("Type your question");
    await user.type(textarea, "hello");
    await user.click(screen.getByRole("button", { name: /send message/i }));

    expect(await screen.findByRole("button", { name: /stop generating/i })).toBeInTheDocument();

    releaseFetch(
      makeStreamingResponse([
        aguiEvent({ type: "RUN_STARTED", threadId: "abc-123", runId: "run-1" }),
        ...textMessageEvents("msg-1", ["hi"]),
        aguiEvent({ type: "RUN_FINISHED", threadId: "abc-123", runId: "run-1" }),
      ]),
    );

    await screen.findByText("hi");
    await screen.findByRole("button", { name: /send message/i });
  });

  it("clicking Stop aborts the in-flight request and shows a stopped state", async () => {
    let capturedSignal: AbortSignal | undefined;
    (fetch as any).mockImplementationOnce((_url: string, options: RequestInit) => {
      capturedSignal = options.signal as AbortSignal;
      return new Promise((_resolve, reject) => {
        capturedSignal!.addEventListener("abort", () => {
          const err = new DOMException("aborted", "AbortError");
          reject(err);
        });
      });
    });

    const user = userEvent.setup();
    render(<App />);
    const textarea = screen.getByLabelText("Type your question");
    await user.type(textarea, "hello");
    await user.click(screen.getByRole("button", { name: /send message/i }));

    const stopBtn = await screen.findByRole("button", { name: /stop generating/i });
    expect(capturedSignal?.aborted).toBe(false);
    await user.click(stopBtn);

    await screen.findByText("Stopped.");
    await screen.findByRole("button", { name: /send message/i });
  });
});
