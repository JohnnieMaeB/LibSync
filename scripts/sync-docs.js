#!/usr/bin/env node
// Copies client/src/ -> docs/ so GitHub Pages serves the same frontend as
// local dev, instead of the two drifting as hand-maintained copies. Run this
// after any change under client/src/ and commit the result; CI fails the
// build if docs/ doesn't match what this script produces (see ci.yml).
"use strict";

const fs = require("fs");
const path = require("path");

const SOURCE_DIR = path.join(__dirname, "..", "client", "src");
const DEST_DIR = path.join(__dirname, "..", "docs");

// Tooling/tests that only make sense in client/src, not on the static site.
const EXCLUDE = new Set(["package.json", "package-lock.json", "script.test.js", "node_modules"]);

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

copyRecursive(SOURCE_DIR, DEST_DIR);
console.log(`Synced ${SOURCE_DIR} -> ${DEST_DIR}`);
