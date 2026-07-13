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
    // docs/ is the GitHub Pages source (served straight from `main`); this
    // makes it a build artifact instead of a hand-copied source tree.
    outDir: "../docs",
    emptyOutDir: true,
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    globals: true,
  },
});
