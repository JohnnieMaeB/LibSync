"use strict";
// Pure helpers for the build-log site generator. No filesystem access here, so
// they can be unit tested directly (see build.test.js).

const { Marked } = require("marked");

const REPO_BLOB = "https://github.com/JohnnieMaeB/LibSync/blob/main/";

function parseFrontmatter(src) {
  const text = src.replace(/^\uFEFF/, "").replace(/\r\n/g, "\n");
  const match = text.match(/^---\n([\s\S]*?)\n---\n?([\s\S]*)$/);
  if (!match) return { data: {}, body: text };
  const data = {};
  for (const line of match[1].split("\n")) {
    const kv = line.match(/^([A-Za-z_][\w-]*):\s*(.*)$/);
    if (!kv) continue;
    data[kv[1]] = kv[2].replace(/^["']|["']$/g, "");
  }
  return { data, body: match[2] };
}

function slugify(text) {
  return text
    .toLowerCase()
    .replace(/['\u2019]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// Path from a page `depth` directories below the blog root back up to it.
// depth 0 = blog/index.html -> "./"; depth 1 = blog/<slug>/index.html -> "../".
function relPrefix(depth) {
  return depth === 0 ? "./" : "../".repeat(depth);
}

function formatDate(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  const months = ["January", "February", "March", "April", "May", "June", "July",
    "August", "September", "October", "November", "December"];
  return `${months[m - 1]} ${d}, ${y}`;
}

// "October 2026" for a YYYY-MM-DD date (case studies are dated by month only).
function monthLabel(iso) {
  return formatDate(iso).replace(/ \d{1,2}, /, " ");
}

// Links in docs/writeups/*.md are relative to the repo ("../../server/...").
// On the site they'd 404, so point them at the file on GitHub instead.
function resolveRepoLink(href, sourceDirInRepo) {
  if (/^([a-z]+:|#|\/\/)/i.test(href)) return href;
  const parts = sourceDirInRepo.split("/").filter(Boolean);
  for (const seg of href.split("/")) {
    if (seg === "..") parts.pop();
    else if (seg !== ".") parts.push(seg);
  }
  return REPO_BLOB + parts.join("/");
}

function renderMarkdown(body, { sourceDirInRepo = null } = {}) {
  const marked = new Marked({
    gfm: true,
    renderer: {
      link(href, title, text) {
        const target = sourceDirInRepo ? resolveRepoLink(href, sourceDirInRepo) : href;
        const t = title ? ` title="${escapeHtml(title)}"` : "";
        return `<a href="${escapeHtml(target)}"${t}>${text}</a>`;
      },
    },
  });
  return marked.parse(body);
}

// Turns one of the LinkedIn drafts (title line, metadata bullets, a ```text
// fenced block holding the post) into a site post. Only the fenced text is
// published; the surrounding review notes are private working notes.
function draftToPost(src, { year = 2026 } = {}) {
  const title = (src.match(/^# (.+)$/m) || [])[1];
  if (!title) throw new Error("Draft has no '# ' title line");
  const dateLine = (src.match(/^- \*\*Date:\*\*\s*(.+)$/m) || [])[1] || "";
  const dm = dateLine.match(/([A-Z][a-z]{2})\s+(\d{1,2})/);
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  if (!dm || months.indexOf(dm[1]) < 0) throw new Error(`Can't read a date from: ${dateLine}`);
  const date = `${year}-${String(months.indexOf(dm[1]) + 1).padStart(2, "0")}-${String(dm[2]).padStart(2, "0")}`;
  const fence = src.match(/```text\n([\s\S]*?)\n```/);
  if (!fence) throw new Error("Draft has no ```text block");
  const partMatch = title.match(/^Part (\d+):\s*(.+?)(?:\s*\(.*\))?$/);
  const isPrologue = /^Prologue:/.test(title);
  const clean = (partMatch ? partMatch[2] : title.replace(/^Prologue:\s*/, "")).trim();
  const lines = fence[1].split("\n").map((l) => l.replace(/^•\s+/, "- "));
  // The LinkedIn hashtag line means nothing on the site; drop it.
  const body = lines.filter((l) => !/^(#[A-Za-z]+\s*)+$/.test(l.trim())).join("\n").trimEnd();
  const order = isPrologue ? 0 : partMatch ? Number(partMatch[1]) : 99;
  const frontmatter = [
    "---",
    `title: ${clean}`,
    `date: ${date}`,
    `order: ${order}`,
    `series: ${isPrologue ? "Prologue" : partMatch ? `Part ${partMatch[1]} of 18` : ""}`,
    "---",
    "",
  ].join("\n");
  return { slug: slugify(clean), markdown: frontmatter + body + "\n", order, date };
}

module.exports = {
  parseFrontmatter, slugify, escapeHtml, relPrefix, formatDate, monthLabel,
  resolveRepoLink, renderMarkdown, draftToPost, REPO_BLOB,
};
