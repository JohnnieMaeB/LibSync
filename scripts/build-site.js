#!/usr/bin/env node
// Runs `vite build` on app/ (optionally overriding VITE_API_BASE_URL) and
// copies the result to an output directory. Used by:
//   - the prod publish workflow (no override — app/.env.production already
//     has the real Render URL baked in), output -> gh-pages branch root
//   - the PR-preview workflow (--api-base-url <dev backend URL>), output ->
//     gh-pages branch's pr-preview/pr-<N>/
//
// Assumes `npm ci` has already been run in app/ — the calling workflow does
// that as its own step (matching ci.yml's pattern); this script only builds
// and copies, it doesn't manage dependencies.
"use strict";

const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

const APP_DIR = path.join(__dirname, "..", "app");
const APP_BUILD_DIR = path.join(APP_DIR, "dist");

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

// VITE_API_BASE_URL is read at build time via `import.meta.env` (see
// app/src/config.ts), so overriding it means rebuilding with the env var
// set, not post-processing the built output the way the old client/src
// config.js string-rewrite did.
function buildApp(apiBaseUrl) {
  const env = { ...process.env };
  if (apiBaseUrl) {
    env.VITE_API_BASE_URL = apiBaseUrl;
  }
  execFileSync("npm", ["run", "build"], { cwd: APP_DIR, env, stdio: "inherit", shell: true });
}

function copyBuildOutput(dest) {
  fs.rmSync(dest, { recursive: true, force: true });
  fs.cpSync(APP_BUILD_DIR, dest, { recursive: true });
}

const { outDir, apiBaseUrl } = parseArgs(process.argv.slice(2));
buildApp(apiBaseUrl);
copyBuildOutput(outDir);
console.log(`Built ${APP_DIR} -> ${outDir}${apiBaseUrl ? ` (VITE_API_BASE_URL=${apiBaseUrl})` : ""}`);
