import { afterEach, describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import axe from "axe-core";
import App from "./App";

// Automated WCAG 2.1 A/AA checks (axe-core) on every patron-facing view.
// jsdom has no layout engine, so color contrast is checked in a real browser
// instead (e2e/a11y.spec.ts); everything else axe can see runs here, on every
// push. Phase 36T, TIER8_PLAN.md §2.8.
async function wcagViolations(container: Element) {
  const results = await axe.run(container, {
    runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"] },
    rules: { "color-contrast": { enabled: false } },
  });
  return results.violations.map((v) => `${v.id}: ${v.help} (${v.nodes.length} node(s))`);
}

describe("accessibility (axe-core, WCAG 2.1 A/AA)", () => {
  afterEach(() => {
    window.history.pushState({}, "", "/");
  });

  it("standalone app has no detectable violations", async () => {
    const { container } = render(<App />);
    await screen.findByRole("navigation", { name: "Conversations" });
    expect(await wcagViolations(container)).toEqual([]);
  });

  it("widget mode has no detectable violations", async () => {
    window.history.pushState({}, "", "/?mode=widget&library=acme&help=https%3A%2F%2Facme.example%2Fask");
    const { container } = render(<App />);
    expect(await wcagViolations(container)).toEqual([]);
  });

  it("the privacy dialog has no detectable violations", async () => {
    const user = userEvent.setup();
    const { container } = render(<App />);
    await user.click(screen.getByRole("button", { name: "How your data is handled" }));
    await screen.findByRole("dialog");
    expect(await wcagViolations(container)).toEqual([]);
  });
});
