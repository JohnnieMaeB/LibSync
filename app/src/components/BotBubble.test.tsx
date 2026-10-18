import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BotBubble } from "./BotBubble";
import type { BotEntry } from "../types";

const entry: BotEntry = {
  kind: "bot",
  id: "b1",
  status: "done",
  blocks: [{ type: "text", key: "t", text: "You can renew up to three times." }],
  cardCount: 0,
  isLatest: true,
  steps: [{ tool: "search_library_policies", query: "renewals" }],
};

function stepsDetails() {
  return screen.getByText("How I found this").closest("details")!;
}

describe("How I found this", () => {
  it("is collapsed by default", () => {
    render(<BotBubble entry={entry} onRegenerate={() => {}} onRetry={() => {}} />);
    expect(stepsDetails().open).toBe(false);
  });

  it("is open when the library teaches the search", () => {
    render(<BotBubble entry={entry} onRegenerate={() => {}} onRetry={() => {}} teachSearch />);
    expect(stepsDetails().open).toBe(true);
  });
});
