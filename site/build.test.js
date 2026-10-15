"use strict";
const test = require("node:test");
const assert = require("node:assert");
const lib = require("./lib");

test("parseFrontmatter reads keys and body, tolerating BOM and CRLF", () => {
  const { data, body } = lib.parseFrontmatter("\uFEFF---\r\ntitle: Hello\r\norder: 2\r\n---\r\nBody\r\n");
  assert.deepStrictEqual(data, { title: "Hello", order: "2" });
  assert.strictEqual(body.trim(), "Body");
});

test("parseFrontmatter returns the whole text when there is none", () => {
  assert.strictEqual(lib.parseFrontmatter("just text").body, "just text");
});

test("relPrefix gives page-relative roots", () => {
  assert.strictEqual(lib.relPrefix(0), "./");
  assert.strictEqual(lib.relPrefix(2), "../../");
});

test("formatDate and monthLabel", () => {
  assert.strictEqual(lib.formatDate("2026-10-06"), "October 6, 2026");
  assert.strictEqual(lib.monthLabel("2026-10-01"), "October 2026");
});

test("resolveRepoLink points repo-relative links at GitHub and leaves others alone", () => {
  assert.strictEqual(
    lib.resolveRepoLink("../../server/evals/README.md", "docs/writeups"),
    lib.REPO_BLOB + "server/evals/README.md",
  );
  assert.strictEqual(lib.resolveRepoLink("https://example.com/x", "docs/writeups"), "https://example.com/x");
  assert.strictEqual(lib.resolveRepoLink("#section", "docs/writeups"), "#section");
});

test("renderMarkdown escapes link targets", () => {
  assert.match(lib.renderMarkdown('[a](https://x.test/?q="1")'), /href="https:\/\/x\.test\/\?q=%22|&quot;/);
});

const DRAFT = [
  "# Part 9: Who the interface quietly locks out (Act II: the interface)",
  "",
  "- **Date:** Tue Dec 15",
  "- **Personalize:** one true line",
  "",
  "---",
  "",
  "```text",
  "First paragraph.",
  "",
  "What that means in code:",
  "\u2022 One thing",
  "\u2022 Another thing",
  "",
  "LibSync build log, Part 9 of 18.",
  "",
  "#Accessibility #ClaudeCode #LibSync",
  "```",
].join("\n");

test("draftToPost publishes only the text block, with bullets and no hashtags or review notes", () => {
  const post = lib.draftToPost(DRAFT);
  assert.strictEqual(post.date, "2026-12-15");
  assert.strictEqual(post.order, 9);
  assert.match(post.markdown, /title: Who the interface quietly locks out\n/);
  assert.match(post.markdown, /series: Part 9 of 18/);
  assert.match(post.markdown, /\n- One thing\n- Another thing/);
  assert.doesNotMatch(post.markdown, /#Accessibility|Personalize/);
});

test("draftToPost treats the Prologue as order 0", () => {
  const src = DRAFT.replace("# Part 9: Who the interface quietly locks out (Act II: the interface)", "# Prologue: Who's building this");
  const post = lib.draftToPost(src);
  assert.strictEqual(post.order, 0);
  assert.match(post.markdown, /series: Prologue/);
});

test("draftToPost fails loudly on a draft with no text block", () => {
  assert.throws(() => lib.draftToPost("# Part 1: X\n\n- **Date:** Tue Oct 13\n"), /text/);
});
