import { defineConfig, devices } from "@playwright/test";

// Real-browser checks the jsdom unit tests can't do (layout, color contrast).
// Runs against the production build, served locally; the backend is mocked
// per test with page.route, so no API keys or network are needed.
export default defineConfig({
  testDir: "e2e",
  reporter: process.env.CI ? [["list"], ["github"]] : "list",
  use: { baseURL: "http://localhost:4173/", ...devices["Desktop Chrome"] },
  projects: [
    { name: "desktop", use: { viewport: { width: 1280, height: 800 } } },
    { name: "phone", use: { viewport: { width: 390, height: 844 } } },
  ],
  webServer: {
    command: "npx vite preview --port 4173 --strictPort",
    url: "http://localhost:4173/",
    reuseExistingServer: !process.env.CI,
  },
});
