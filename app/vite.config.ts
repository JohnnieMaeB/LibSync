/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      // Static-asset caching only (Tier 5 §4) — this is installability, not
      // offline chat, which would need the backend to be cacheable too.
      workbox: {
        globPatterns: ["**/*.{js,css,html,png,svg,ico}"],
      },
      manifest: {
        name: "LibSync",
        short_name: "LibSync",
        description: "Your personal AI library assistant.",
        theme_color: "#ffd166",
        background_color: "#000000",
        display: "standalone",
        icons: [
          { src: "icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
          { src: "icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
          { src: "icon-512-maskable.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
        ],
      },
    }),
  ],
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
