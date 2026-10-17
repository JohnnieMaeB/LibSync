import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";
import { API_BASE_URL } from "./config";

// Builds one AG-UI SSE event chunk, matching the wire format encoded by
// pydantic_ai's AGUIEventStream: a single `data: {...}` line per event.
function aguiEvent(payload: Record<string, unknown>) {
  return `data: ${JSON.stringify(payload)}\n\n`;
}

function makeStreamingResponse(chunks: string[]) {
  let index = 0;
  const encoder = new TextEncoder();
  return {
    ok: true,
    status: 200,
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

// Answers fetch by URL: the library-settings lookup (Tier 8 Phase 30) gets
// `library` (404 by default), and /agent gets the given SSE stream.
function routeFetch(agentResponse: unknown, library: Record<string, unknown> | null = null) {
  (fetch as any).mockImplementation(async (url: string) => {
    if (String(url).includes("/libraries/")) {
      return library ? { ok: true, status: 200, json: async () => library } : { ok: false, status: 404 };
    }
    return agentResponse;
  });
}

function agentCall() {
  return (fetch as any).mock.calls.find(([url]: [string]) => String(url).endsWith("/agent"));
}

// Sets the URL loader.js's iframe would load (see app/public/loader.js) so
// App() takes the widget branch — see widget.ts's getWidgetConfig().
function setWidgetUrl(search: string) {
  window.history.pushState({}, "", `/${search}`);
}

describe("Widget mode (Tier 6)", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    window.history.pushState({}, "", "/");
  });

  it("renders the compact shell with no conversation sidebar", () => {
    setWidgetUrl("?mode=widget&library=acme-library");
    render(<App />);

    expect(document.querySelector(".app-shell.compact")).not.toBeNull();
    expect(screen.queryByRole("navigation", { name: "Conversations" })).toBeNull();
    expect(screen.queryByRole("button", { name: "New chat" })).toBeNull();
  });

  it("posts messages with an X-LibSync-Library header carrying the loader's data-library id", async () => {
    setWidgetUrl("?mode=widget&library=acme-library");
    routeFetch(
      makeStreamingResponse([
        aguiEvent({ type: "RUN_STARTED", threadId: "t1", runId: "r1" }),
        ...textMessageEvents("m1", ["widget reply"]),
        aguiEvent({ type: "RUN_FINISHED", threadId: "t1", runId: "r1" }),
      ]),
    );

    const user = userEvent.setup();
    render(<App />);
    const textarea = screen.getByLabelText("Type your question");
    await user.type(textarea, "Hello");
    await user.click(screen.getByRole("button", { name: /send message/i }));

    await screen.findByText("widget reply");

    const [url, options] = agentCall();
    expect(url).toBe(`${API_BASE_URL}/agent`);
    expect(options.headers["X-LibSync-Library"]).toBe("acme-library");
  });

  it("forwards the loader's data-tools as an X-LibSync-Tools header and links its help URL", async () => {
    setWidgetUrl(
      "?mode=widget&library=acme-library&tools=policies%2Ccatalog&help=" +
        encodeURIComponent("https://acme.example/ask"),
    );
    routeFetch(
      makeStreamingResponse([
        aguiEvent({ type: "RUN_STARTED", threadId: "t1", runId: "r1" }),
        ...textMessageEvents("m1", ["ok"]),
        aguiEvent({ type: "RUN_FINISHED", threadId: "t1", runId: "r1" }),
      ]),
    );

    const user = userEvent.setup();
    render(<App />);
    expect(screen.getByRole("link", { name: "Talk to a librarian" })).toHaveAttribute(
      "href",
      "https://acme.example/ask",
    );
    await user.type(screen.getByLabelText("Type your question"), "Hello");
    await user.click(screen.getByRole("button", { name: /send message/i }));
    await screen.findByText("ok");

    const [, options] = agentCall();
    expect(options.headers["X-LibSync-Tools"]).toBe("policies,catalog");
  });

  it("clicking the close button posts libsync:close to the parent window (loader.js's postMessage contract)", async () => {
    setWidgetUrl("?mode=widget&library=acme-library");
    const postMessage = vi.fn();
    vi.stubGlobal("parent", { postMessage });

    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: "Close chat" }));

    expect(postMessage).toHaveBeenCalledWith({ type: "libsync:close" }, "*");
  });

  it("shows a librarian contact instead of the chat when the library switched the assistant off", async () => {
    setWidgetUrl("?mode=widget&library=acme-library");
    routeFetch(undefined, { id: "acme-library", name: "Acme", help_url: "mailto:ask@acme.example", ai_enabled: false });
    render(<App />);
    expect(await screen.findByText(/turned the AI assistant off/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Talk to a librarian" })).toHaveAttribute("href", "mailto:ask@acme.example");
    expect(screen.queryByLabelText("Type your question")).toBeNull();
  });

  it("offers 'not helpful' only when the library collects feedback, and sends the exchange", async () => {
    setWidgetUrl("?mode=widget&library=acme-library");
    const feedbackBodies: unknown[] = [];
    (fetch as any).mockImplementation(async (url: string, init?: RequestInit) => {
      if (String(url).includes("/libraries/")) {
        return { ok: true, json: async () => ({ id: "acme-library", name: "Acme", ai_enabled: true, feedback_enabled: true }) };
      }
      if (String(url).endsWith("/feedback")) {
        feedbackBodies.push(JSON.parse(String(init?.body)));
        return { ok: true, json: async () => ({ sent: true }) };
      }
      return makeStreamingResponse([
        aguiEvent({ type: "RUN_STARTED", threadId: "t1", runId: "r1" }),
        ...textMessageEvents("m1", ["We close at 8."]),
        aguiEvent({ type: "RUN_FINISHED", threadId: "t1", runId: "r1" }),
      ]);
    });
    const user = userEvent.setup();
    render(<App />);
    await user.type(screen.getByLabelText("Type your question"), "When do you close?");
    await user.click(screen.getByRole("button", { name: /send message/i }));
    await screen.findByText("We close at 8.");
    await user.click(await screen.findByRole("button", { name: /Not helpful: send this question and answer/ }));
    expect(await screen.findByText(/Sent to library staff/)).toBeInTheDocument();
    expect(feedbackBodies).toEqual([{ question: "When do you close?", answer: "We close at 8." }]);
  });

  it("does not offer 'not helpful' without library feedback", async () => {
    setWidgetUrl("?mode=widget&library=acme-library");
    routeFetch(
      makeStreamingResponse([
        aguiEvent({ type: "RUN_STARTED", threadId: "t1", runId: "r1" }),
        ...textMessageEvents("m1", ["ok"]),
        aguiEvent({ type: "RUN_FINISHED", threadId: "t1", runId: "r1" }),
      ]),
    );
    const user = userEvent.setup();
    render(<App />);
    await user.type(screen.getByLabelText("Type your question"), "Hi");
    await user.click(screen.getByRole("button", { name: /send message/i }));
    await screen.findByText("ok");
    expect(screen.queryByRole("button", { name: /Not helpful/ })).toBeNull();
  });

  it("keeps the chat when the settings lookup fails", async () => {
    setWidgetUrl("?mode=widget&library=acme-library");
    (fetch as any).mockRejectedValue(new Error("offline"));
    render(<App />);
    expect(screen.getByLabelText("Type your question")).toBeInTheDocument();
  });

  it("standalone mode (no mode=widget) still renders the full sidebar shell", () => {
    render(<App />);
    expect(document.querySelector(".app-shell.compact")).toBeNull();
    expect(screen.getByRole("navigation", { name: "Conversations" })).toBeInTheDocument();
  });
});
