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
    (fetch as any).mockResolvedValueOnce(
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

    const [url, options] = (fetch as any).mock.calls[0];
    expect(url).toBe(`${API_BASE_URL}/agent`);
    expect(options.headers["X-LibSync-Library"]).toBe("acme-library");
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

  it("standalone mode (no mode=widget) still renders the full sidebar shell", () => {
    render(<App />);
    expect(document.querySelector(".app-shell.compact")).toBeNull();
    expect(screen.getByRole("navigation", { name: "Conversations" })).toBeInTheDocument();
  });
});
