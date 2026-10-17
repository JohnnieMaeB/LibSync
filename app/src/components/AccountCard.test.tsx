import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { AccountCard } from "./AccountCard";
import { blocksToPlainText } from "../lib/plainText";

const DATA = {
  counts: { charged: 2, overdue: 1, holds: 0 },
  items: { charged: ["Dune", "Beloved"], overdue: ["Dune"], holds: [] },
  fees: "1.50",
};

describe("AccountCard (Tier 9 Phase 38)", () => {
  it("lists the patron's items by section with counts", () => {
    render(<AccountCard data={DATA} />);
    const card = screen.getByRole("region", { name: "Your library account" });
    expect(within(card).getByRole("heading", { name: "Checked out (2)" })).toBeInTheDocument();
    expect(within(card).getByRole("heading", { name: "On hold (0)" })).toBeInTheDocument();
    expect(within(card).getAllByText("Dune")).toHaveLength(2);
    expect(screen.getByText("Fees owed: $1.50")).toBeInTheDocument();
  });

  it("hides fees when there are none", () => {
    render(<AccountCard data={{ ...DATA, fees: "0.00" }} />);
    expect(screen.queryByText(/Fees owed/)).toBeNull();
  });

  it("copies as readable text", () => {
    expect(blocksToPlainText([{ type: "account", key: "k", data: DATA }])).toBe(
      "Checked out: Dune, Beloved. Overdue: Dune. On hold: none",
    );
  });
});
