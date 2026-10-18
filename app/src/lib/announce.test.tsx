import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { replyAnnouncement } from "./announce";
import { ChatBox } from "../components/ChatBox";
import { en } from "../i18n/messages";
import type { BotEntry, ChatEntry } from "../types";

function bot(extra: Partial<BotEntry>): BotEntry {
  return { kind: "bot", id: "b", status: "done", blocks: [], cardCount: 0, isLatest: true, ...extra };
}

describe("screen-reader announcements", () => {
  it("say answering, each search, then the whole reply once, without markdown or emoji", () => {
    expect(replyAnnouncement(bot({ status: "loading" }), en)).toBe("LibSync is answering…");
    expect(replyAnnouncement(bot({ status: "streaming" }), en)).toBe("");
    expect(replyAnnouncement(bot({ status: "tool", toolLabel: "📚 Checking library policies" }), en)).toBe(
      "Checking library policies",
    );
    const done = bot({
      blocks: [
        { type: "text", key: "t", text: "**Renewals:** up to 3 times 📚" },
        {
          type: "book",
          key: "b",
          number: 1,
          data: { title: "Beloved", author: "Toni Morrison", year: 1987, availability: "available" },
        },
      ],
    });
    expect(replyAnnouncement(done, en)).toBe(
      "LibSync replied: Renewals: up to 3 times Beloved (1987), by Toni Morrison, available.",
    );
  });

  function announcer() {
    return screen.getByRole("status", { hidden: true });
  }

  const noop = () => {};

  it("aren't made for replies already there when a conversation opens", () => {
    const history: ChatEntry[] = [bot({ blocks: [{ type: "text", key: "t", text: "Old answer" }] })];
    render(<ChatBox entries={history} chipsHidden onSelectSuggestion={noop} onRegenerate={noop} onRetry={noop} />);
    expect(announcer()).toHaveTextContent("");
  });

  it("come from the status element, while the conversation itself is not a live region", () => {
    const { rerender } = render(
      <ChatBox entries={[]} chipsHidden onSelectSuggestion={noop} onRegenerate={noop} onRetry={noop} />,
    );
    const streaming: ChatEntry[] = [{ kind: "user", id: "u", text: "q" }, bot({ id: "new", status: "loading" })];
    rerender(<ChatBox entries={streaming} chipsHidden onSelectSuggestion={noop} onRegenerate={noop} onRetry={noop} />);
    expect(announcer()).toHaveTextContent("LibSync is answering…");
    const log = screen.getByRole("log");
    expect(log).toHaveAttribute("aria-live", "off");
    expect(log).toHaveAttribute("aria-busy", "true");
  });
});
