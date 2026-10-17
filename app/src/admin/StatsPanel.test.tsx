import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StatsPanel } from "./StatsPanel";

const STATS = {
  days: 30,
  turns: 40,
  errors: 1,
  error_rate: 0.025,
  daily: [{ day: "2026-10-15", turns: 40, errors: 1 }],
  tools: [{ tool: "search_library_policies", calls: 12 }],
};

describe("StatsPanel (Tier 8 Phase 33)", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("shows totals and labeled tables", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, json: async () => STATS })));
    render(<StatsPanel libraryId="springfield-pl" accessToken="t" />);
    expect(await screen.findByText("40", { selector: "dd" })).toBeInTheDocument();
    expect(screen.getByText("1 (2.5%)")).toBeInTheDocument();
    const lookups = screen.getByRole("table", { name: "What the assistant looked up" });
    expect(within(lookups).getByRole("rowheader", { name: "Library policies" })).toBeInTheDocument();
  });

  it("explains when statistics aren't set up", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: false, json: async () => ({ detail: "Usage statistics aren't set up (needs a Logfire read token)." }) })),
    );
    render(<StatsPanel libraryId="springfield-pl" accessToken="t" />);
    expect(await screen.findByText(/aren't set up/)).toBeInTheDocument();
  });

  it("asks for a different period", async () => {
    const fetchMock = vi.fn(async (_url: string) => ({ ok: true, json: async () => STATS }));
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<StatsPanel libraryId="springfield-pl" accessToken="t" />);
    await user.selectOptions(screen.getByLabelText("Period"), "7");
    expect(String(fetchMock.mock.calls[fetchMock.mock.calls.length - 1]?.[0])).toContain("days=7");
  });
});
