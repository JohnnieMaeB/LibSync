#!/usr/bin/env node
// Copies client/src/ -> an output directory, optionally overriding
// API_BASE_URL along the way. Used by:
//   - the prod publish workflow (no override — client/src/config.js already
//     has the real Render URL baked in), output -> gh-pages branch root
//   - the PR-preview workflow (--api-base-url <dev backend URL>), output ->
//     gh-pages branch's pr-preview/pr-<N>/
//
// Replaces the old scripts/sync-docs.js + hand-committed docs/ folder now
// that GitHub Pages publishes from the gh-pages branch via GitHub Actions
// instead of a manually-synced main/docs.
"use strict";

const fs = require("fs");
const path = require("path");

const SOURCE_DIR = path.join(__dirname, "..", "client", "src");

// Tooling/tests that only make sense in client/src, not on the static site.
const EXCLUDE = new Set(["package.json", "package-lock.json", "script.test.js", "node_modules"]);

function parseArgs(argv) {
  const args = { outDir: null, apiBaseUrl: null };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--out" && argv[i + 1]) {
      args.outDir = argv[++i];
    } else if (argv[i] === "--api-base-url" && argv[i + 1]) {
      args.apiBaseUrl = argv[++i];
    }
  }
  if (!args.outDir) {
    console.error("Usage: node build-site.js --out <dir> [--api-base-url <url>]");
    process.exit(1);
  }
  return args;
}

function copyRecursive(src, dest) {
  const entries = fs.readdirSync(src, { withFileTypes: true });
  fs.mkdirSync(dest, { recursive: true });

  for (const entry of entries) {
    if (EXCLUDE.has(entry.name)) continue;
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);

    if (entry.isDirectory()) {
      copyRecursive(srcPath, destPath);
    } else {
      fs.copyFileSync(srcPath, destPath);
    }
  }
}

// Rewrites the `const API_BASE_URL = "...";` line — the same pattern
// client/src/config.js already uses, just pointed at a different backend.
function overrideApiBaseUrl(outDir, apiBaseUrl) {
  const configPath = path.join(outDir, "config.js");
  const original = fs.readFileSync(configPath, "utf8");
  const rewritten = original.replace(
    /const API_BASE_URL = ".*?";/,
    `const API_BASE_URL = "${apiBaseUrl}";`
  );
  if (rewritten === original) {
    console.error(`Could not find "const API_BASE_URL = ...;" in ${configPath} to override.`);
    process.exit(1);
  }
  fs.writeFileSync(configPath, rewritten);
}

const { outDir, apiBaseUrl } = parseArgs(process.argv.slice(2));
copyRecursive(SOURCE_DIR, outDir);
if (apiBaseUrl) {
  overrideApiBaseUrl(outDir, apiBaseUrl);
}
console.log(`Built ${SOURCE_DIR} -> ${outDir}${apiBaseUrl ? ` (API_BASE_URL=${apiBaseUrl})` : ""}`);
