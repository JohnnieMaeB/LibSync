#!/usr/bin/env node
// Builds the LibSync build-log site into <out>/ (published at /blog/ on GitHub
// Pages by scripts/build-site.js). Zero framework: markdown in, static HTML out.
//   site/posts/*.md        build-log posts (frontmatter: title, date, order, series)
//   site/about.md          the About page
//   docs/writeups/*.md     engineering case studies, published from their repo source
"use strict";

const fs = require("fs");
const path = require("path");
const {
  parseFrontmatter, escapeHtml, relPrefix, formatDate, monthLabel, renderMarkdown,
} = require("./lib");

const SITE_URL = (process.env.SITE_URL || "https://johnniemaeb.github.io/LibSync").replace(/\/$/, "");
const REPO_URL = "https://github.com/JohnnieMaeB/LibSync";
const SITE_NAME = "LibSync build log";
const TAGLINE = "An AI assistant for public libraries, built in the open. I architect; Claude Code builds.";
const ROOT = path.join(__dirname, "..");

function parseArgs(argv) {
  const out = argv.indexOf("--out");
  if (out < 0 || !argv[out + 1]) {
    console.error("Usage: node build.js --out <dir> [--today YYYY-MM-DD]");
    process.exit(1);
  }
  const t = argv.indexOf("--today");
  return { outDir: argv[out + 1], today: t >= 0 ? argv[t + 1] : new Date().toISOString().slice(0, 10) };
}

// `depth` = how many directories below the blog root this page sits, so every
// link can be relative (the same build is served from /LibSync/blog/ in
// production and /LibSync/pr-preview/pr-N/blog/ in PR previews).
function layout({ title, description, depth, body, pagePath, type = "website", noindex = false }) {
  const root = relPrefix(depth);
  const fullTitle = pagePath === "" ? SITE_NAME : `${title} | ${SITE_NAME}`;
  const canonical = `${SITE_URL}/blog/${pagePath}`;
  const image = `${SITE_URL}/blog/assets/social.png`;
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${escapeHtml(fullTitle)}</title>
<meta name="description" content="${escapeHtml(description)}">
${noindex ? '<meta name="robots" content="noindex, nofollow">' : ""}
<link rel="canonical" href="${canonical}">
<link rel="alternate" type="application/atom+xml" title="${SITE_NAME}" href="${root}feed.xml">
<link rel="stylesheet" href="${root}assets/style.css">
<meta property="og:type" content="${type}">
<meta property="og:title" content="${escapeHtml(title)}">
<meta property="og:description" content="${escapeHtml(description)}">
<meta property="og:url" content="${canonical}">
<meta property="og:image" content="${image}">
<meta name="twitter:card" content="summary_large_image">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site">
<a class="brand" href="${root}">LibSync build log</a>
<nav aria-label="Site"><ul>
<li><a href="${root}about/">About</a></li>
<li><a href="${root}../">Live demo</a></li>
<li><a href="${REPO_URL}">GitHub</a></li>
<li><a href="${root}feed.xml">RSS</a></li>
</ul></nav>
</header>
<main id="main">
${body}
</main>
<footer class="site">
<p>MIT licensed. Views are my own. Built with Claude Code; posts are drafted with Claude's help and edited by me.</p>
</footer>
</body>
</html>
`;
}

function readPosts(today) {
  const dir = path.join(__dirname, "posts");
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir)
    .filter((f) => f.endsWith(".md"))
    .map((f) => {
      const { data, body } = parseFrontmatter(fs.readFileSync(path.join(dir, f), "utf8"));
      if (!data.title || !data.date) throw new Error(`${f}: needs title and date in frontmatter`);
      const firstPara = body.trim().split(/\n\s*\n/)[0].replace(/[*_`#>]/g, "").replace(/\s+/g, " ");
      return {
        kind: "post",
        slug: f.replace(/\.md$/, ""),
        title: data.title,
        date: data.date,
        order: Number(data.order ?? 99),
        series: data.series || "",
        unlisted: data.unlisted === "true",
        description: data.description || firstPara.slice(0, 200),
        html: renderMarkdown(body),
      };
    })
    // Listed posts wait for their date; unlisted ones are always built (and never linked).
    .filter((p) => p.unlisted || p.date <= today)
    .sort((a, b) => a.order - b.order);
}

function readCaseStudies() {
  const dir = path.join(ROOT, "docs", "writeups");
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir)
    .filter((f) => /^\d{4}-\d{2}-.+\.md$/.test(f))
    .map((f) => {
      let { body } = parseFrontmatter(fs.readFileSync(path.join(dir, f), "utf8"));
      const title = (body.match(/^# (.+)$/m) || [null, f])[1];
      body = body.replace(/^# .+\n/, "");
      const [y, m] = f.split("-");
      const para = body.split(/\n\s*\n/).map((p) => p.trim()).find((p) => p && !p.startsWith("*")) || "";
      return {
        kind: "case-study",
        slug: f.replace(/\.md$/, ""),
        title,
        date: `${y}-${m}-01`,
        description: para.replace(/\[([^\]]+)\]\([^)]*\)/g, "$1").replace(/[*_`]/g, "").replace(/\s+/g, " ").slice(0, 200),
        html: renderMarkdown(body, { sourceDirInRepo: "docs/writeups" }),
      };
    })
    .sort((a, b) => b.date.localeCompare(a.date));
}

function write(outDir, rel, content) {
  const file = path.join(outDir, rel);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, content);
}

function itemUrl(item, prefix) {
  return item.kind === "case-study" ? `${prefix}case-studies/${item.slug}/` : `${prefix}${item.slug}/`;
}

function listItem(item) {
  const label = item.kind === "case-study"
    ? monthLabel(item.date)
    : (item.series ? `${item.series} · ` : "") + formatDate(item.date);
  return `<li><a href="${itemUrl(item, "./")}">${escapeHtml(item.title)}</a><p>${escapeHtml(label)}. ${escapeHtml(item.description)}</p></li>`;
}

function buildIndex(posts, studies) {
  const postsHtml = posts.length
    ? `<ul class="posts">${posts.map(listItem).join("")}</ul>`
    : `<p>The first posts are on their way. They appear here, in order, as each one goes out on LinkedIn.</p>`;
  const body = `<p class="kicker">Build log</p>
<h1>${escapeHtml(TAGLINE)}</h1>
<p>LibSync answers library-desk questions from a library's own policies and says so when it can't check something. I'm the architect, Claude Code is the builder, and this is where I write down what it built, what it got wrong, and what I did about it. <a href="about/">More about the project</a>.</p>
<h2>Posts</h2>
${postsHtml}
<h2>Case studies</h2>
<ul class="posts">${studies.map(listItem).join("")}</ul>`;
  return layout({ title: SITE_NAME, description: TAGLINE, depth: 0, body, pagePath: "" });
}

function buildPost(post, posts) {
  // Series navigation stays within a visibility class, so a listed post never links to an unlisted one.
  const pool = posts.filter((p) => p.unlisted === post.unlisted);
  const i = pool.indexOf(post);
  const prev = pool[i - 1];
  const next = pool[i + 1];
  const nav = `<nav class="series-nav" aria-label="Series">
<span>${prev ? `<a href="../${prev.slug}/">&larr; ${escapeHtml(prev.title)}</a>` : ""}</span>
<span>${next ? `<a href="../${next.slug}/">${escapeHtml(next.title)} &rarr;</a>` : ""}</span>
</nav>`;
  const body = `<p class="kicker">${escapeHtml(post.series || "Build log")}</p>
<h1>${escapeHtml(post.title)}</h1>
<p class="meta"><time datetime="${post.date}">${formatDate(post.date)}</time></p>
${post.html}
${nav}`;
  return layout({ title: post.title, description: post.description, depth: 1, body, pagePath: `${post.slug}/`, type: "article", noindex: post.unlisted });
}

function buildCaseStudy(study) {
  const body = `<p class="kicker">Case study</p>
<h1>${escapeHtml(study.title)}</h1>
<p class="meta">${monthLabel(study.date)} · <a href="${REPO_URL}/blob/main/docs/writeups/${study.slug}.md">source in the repo</a></p>
${study.html}`;
  return layout({ title: study.title, description: study.description, depth: 2, body, pagePath: `case-studies/${study.slug}/`, type: "article" });
}

function buildAbout() {
  const { data, body } = parseFrontmatter(fs.readFileSync(path.join(__dirname, "about.md"), "utf8"));
  const html = `<h1>${escapeHtml(data.title)}</h1>\n${renderMarkdown(body)}`;
  return layout({ title: data.title, description: data.description, depth: 1, body: html, pagePath: "about/" });
}

function buildFeed(items) {
  const entries = items.map((it) => {
    const url = itemUrl(it, `${SITE_URL}/blog/`);
    return `<entry><title>${escapeHtml(it.title)}</title><link href="${url}"/><id>${url}</id><updated>${it.date}T00:00:00Z</updated><summary>${escapeHtml(it.description)}</summary></entry>`;
  }).join("\n");
  const updated = items.map((i) => i.date).sort().pop() || "2026-10-01";
  return `<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>${SITE_NAME}</title><subtitle>${escapeHtml(TAGLINE)}</subtitle><link href="${SITE_URL}/blog/feed.xml" rel="self"/><link href="${SITE_URL}/blog/"/><id>${SITE_URL}/blog/</id><updated>${updated}T00:00:00Z</updated><author><name>Johnnie Boutwell</name></author>
${entries}
</feed>
`;
}

function buildSitemap(items) {
  const urls = [`${SITE_URL}/`, `${SITE_URL}/blog/`, `${SITE_URL}/blog/about/`]
    .concat(items.map((it) => itemUrl(it, `${SITE_URL}/blog/`)));
  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls.map((u) => `<url><loc>${u}</loc></url>`).join("\n")}
</urlset>
`;
}

function main() {
  const { outDir, today } = parseArgs(process.argv.slice(2));
  const allPosts = readPosts(today);
  const posts = allPosts.filter((p) => !p.unlisted);
  const studies = readCaseStudies();
  fs.rmSync(outDir, { recursive: true, force: true });
  write(outDir, "index.html", buildIndex(posts, studies));
  write(outDir, "about/index.html", buildAbout());
  for (const p of allPosts) write(outDir, `${p.slug}/index.html`, buildPost(p, allPosts));
  for (const s of studies) write(outDir, `case-studies/${s.slug}/index.html`, buildCaseStudy(s));
  const all = [...posts, ...studies].sort((a, b) => b.date.localeCompare(a.date));
  write(outDir, "feed.xml", buildFeed(all));
  write(outDir, "sitemap.xml", buildSitemap([...posts, ...studies]));
  fs.mkdirSync(path.join(outDir, "assets"), { recursive: true });
  fs.copyFileSync(path.join(__dirname, "assets", "style.css"), path.join(outDir, "assets", "style.css"));
  const social = path.join(__dirname, "assets", "social.png");
  if (fs.existsSync(social)) fs.copyFileSync(social, path.join(outDir, "assets", "social.png"));
  console.log(`Built blog: ${posts.length} listed + ${allPosts.length - posts.length} unlisted posts, ${studies.length} case studies -> ${outDir}`);
}

if (require.main === module) main();
