/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // Relative base so the build works under GitHub Pages' project-page
  // subpath (https://<user>.github.io/LibSync/) without hardcoding the repo
  // name, matching how client/src's plain <script>/<link> tags used relative
  // paths for the same reason.
  base: "./",
  build: {
    // Default outDir (app/dist, gitignored). GitHub Pages is published from
    // the gh-pages branch by scripts/build-site.js + the deploy workflows,
    // not from a committed docs/ tree — see deploy-pages.yml.
    outDir: "dist",
    emptyOutDir: true,
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    globals: true,
  },
});
