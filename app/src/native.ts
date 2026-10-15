import { Capacitor } from "@capacitor/core";

// Tier 7: setup that only applies inside the Android/iOS shell (Capacitor).
// In a browser every branch here is skipped, so the web app is unchanged.
export const isNative = Capacitor.isNativePlatform();

export async function initNativeShell(): Promise<void> {
  if (!isNative) return;
  const [{ StatusBar, Style }, { SplashScreen }] = await Promise.all([
    import("@capacitor/status-bar"),
    import("@capacitor/splash-screen"),
  ]);
  // Light text on LibSync's black background.
  await StatusBar.setStyle({ style: Style.Dark }).catch(() => {});
  await SplashScreen.hide().catch(() => {});
}

// The service worker exists for web installability (Tier 5). Inside the native
// shell the files already ship with the app, and a worker could keep serving an
// older cached bundle after an app update, so it's registered on the web only.
export async function registerServiceWorker(): Promise<void> {
  if (isNative) return;
  const { registerSW } = await import("virtual:pwa-register");
  registerSW({ immediate: true });
}
