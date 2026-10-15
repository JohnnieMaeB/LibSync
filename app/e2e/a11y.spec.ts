import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

// WCAG 2.1 A/AA checks in a real browser, including color contrast, which
// jsdom can't evaluate (see src/a11y.test.tsx). Phase 36T, TIER8_PLAN.md §2.8;
// results feed docs/compliance/ACCESSIBILITY_CONFORMANCE_REPORT.md.
const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];

async function expectNoViolations(page: Page) {
  const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
  const summary = results.violations.map(
    (v) => `${v.id} (${v.impact}): ${v.help} — ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`,
  );
  expect(summary).toEqual([]);
}

function sse(events: Record<string, unknown>[]) {
  return events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join("");
}

// One reply carrying every card type, so their colors and structure are audited too.
const CARD_REPLY = sse([
  { type: "RUN_STARTED", threadId: "t", runId: "r" },
  { type: "TEXT_MESSAGE_START", messageId: "m", role: "assistant" },
  { type: "TEXT_MESSAGE_CONTENT", messageId: "m", delta: "Here's what I found. **Late fees** are $0.25 per day." },
  { type: "TEXT_MESSAGE_END", messageId: "m" },
  {
    type: "CUSTOM",
    name: "book_card",
    value: {
      title: "Project Hail Mary",
      author: "Andy Weir",
      first_publish_year: 2021,
      availability: "lendable",
      cover_url: null,
      url: "https://openlibrary.org/works/OL21745884W",
    },
  },
  {
    type: "CUSTOM",
    name: "research_results",
    value: {
      intro: "Found 1 work:",
      works: [
        {
          title: "ChatGPT for good?",
          authors: "Kasneci et al.",
          year: 2023,
          doi: "10.1016/j.lindif.2023.102274",
          citation_count: 4000,
          is_oa: true,
          abstract: "An abstract.",
        },
      ],
    },
  },
  {
    type: "CUSTOM",
    name: "citation",
    value: {
      formatted: "Kasneci, E., et al. (2023). ChatGPT for good? Learning and Individual Differences, 103.",
      doi: "10.1016/j.lindif.2023.102274",
      style: "apa",
      available_styles: ["apa", "chicago", "mla"],
    },
  },
  { type: "RUN_FINISHED", threadId: "t", runId: "r" },
]);

test.beforeEach(async ({ page }) => {
  await page.route("**/agent", (route) =>
    route.fulfill({ status: 200, contentType: "text/event-stream", body: CARD_REPLY }),
  );
});

test("standalone app", async ({ page }) => {
  await page.goto("./");
  await expect(page.getByRole("button", { name: "How your data is handled" })).toBeVisible();
  await expectNoViolations(page);
});

test("widget mode", async ({ page }) => {
  await page.goto("./?mode=widget&library=acme&help=https%3A%2F%2Facme.example%2Fask");
  await expect(page.getByRole("link", { name: "Talk to a librarian" })).toBeVisible();
  await expectNoViolations(page);
});

test("privacy dialog", async ({ page }) => {
  await page.goto("./");
  await page.getByRole("button", { name: "How your data is handled" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expectNoViolations(page);
});

test("a reply with book, research and citation cards", async ({ page }) => {
  await page.goto("./");
  await page.getByLabel("Type your question").fill("Show me everything");
  await page.getByRole("button", { name: /send message/i }).click();
  await expect(page.getByText("Project Hail Mary")).toBeVisible();
  await expect(page.getByText(/ChatGPT for good\?/).first()).toBeVisible();
  await expectNoViolations(page);
});

test("keyboard: Tab reaches the composer and Enter on the disclosure link opens the dialog", async ({ page }) => {
  await page.goto("./?mode=widget&library=acme");
  const disclosure = page.getByRole("button", { name: "How your data is handled" });
  await disclosure.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(disclosure).toBeFocused();
});
