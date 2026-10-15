#!/usr/bin/env node
// Copies one LinkedIn draft from the (gitignored) blog-drafts/ folder into
// site/posts/ as a publishable post. Only the draft's ```text block is
// published; the review notes around it never leave your machine.
//   node site/publish-post.js 03            (matches blog-drafts/03-*.md)
//   node site/publish-post.js 03 --live    (listed on the blog index, feed and sitemap)
//
// By default a post is *unlisted*: it gets a page, but it isn't linked from the
// index, feed or sitemap, and it carries noindex. Unlisted is not private: the
// source is in a public repo and anyone with the URL can read the page.
"use strict";

const fs = require("fs");
const path = require("path");
const { draftToPost } = require("./lib");

const draftsDir = path.join(__dirname, "..", "blog-drafts");
const arg = process.argv[2];
if (!arg) {
  console.error("Usage: node site/publish-post.js <draft number, e.g. 03>");
  process.exit(1);
}
const match = fs.readdirSync(draftsDir).find((f) => f.endsWith(".md") && f.startsWith(arg.padStart(2, "0") + "-"));
if (!match) {
  console.error(`No draft in blog-drafts/ starts with "${arg.padStart(2, "0")}-"`);
  process.exit(1);
}
const live = process.argv.includes("--live");
const post = draftToPost(fs.readFileSync(path.join(draftsDir, match), "utf8"), { unlisted: !live });
const dest = path.join(__dirname, "posts", match);
fs.writeFileSync(dest, post.markdown);
console.log(`Wrote ${path.relative(process.cwd(), dest)} (dated ${post.date}, ${live ? "listed" : "unlisted"}).`);
console.log("Check it for [Personalize] lines or unresolved placeholders before committing.");
