import type { CapacitorConfig } from "@capacitor/cli";

// Tier 7: the Tier 5 app in a native shell for Android and iOS. The web build
// (dist/) is bundled into the app; it talks to the same production backend as
// the web app. TIER7_PLAN.md.
const config: CapacitorConfig = {
  appId: "io.github.johnniemaeb.libsync",
  appName: "LibSync",
  webDir: "dist",
  backgroundColor: "#000000",
  plugins: {
    SplashScreen: {
      launchShowDuration: 800,
      backgroundColor: "#000000",
      showSpinner: false,
    },
    StatusBar: {
      style: "DARK",
      backgroundColor: "#000000",
      overlaysWebView: false,
    },
  },
};

export default config;
