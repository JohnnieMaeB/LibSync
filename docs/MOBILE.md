# LibSync on Android and iOS (Tier 7)

The mobile apps are the same React app as the website, wrapped in a native shell with
[Capacitor](https://capacitorjs.com/). They talk to the same backend, show the same AI disclosure and privacy
dialog, and keep conversation history on the device, like the web app. Everything here is $0; publishing to the
App Store or Google Play is a separate, paid decision (TIER7_PLAN.md Phase 29).

## Android: install the APK

Every pull request and push to `main` that touches `app/` builds a debug APK in GitHub Actions.

1. Open the latest **Mobile Builds** run under the repo's Actions tab and download the
   `libsync-android-debug-apk` artifact (a zip containing `app-debug.apk`).
2. Copy the APK to an Android phone and open it. Android will ask you to allow installs from that source
   (Settings → Apps → Special app access → Install unknown apps).

It's a debug build signed with a development key, which is fine for sideloading and testing. A Play Store release
needs a release key and the $25 Play Console fee.

## iOS: run on your own iPhone (requires a Mac)

CI builds the iOS project for the simulator on every change, so it's known to compile. Installing on a phone
needs a Mac with Xcode, using Apple's free personal-team signing:

```bash
cd app
npm ci
npm run build
npx cap sync ios
npx cap open ios
```

In Xcode, select the **App** target → Signing & Capabilities → choose your Apple ID as the team, connect the
phone, and press Run. Free personal-team builds **expire after 7 days**; re-run from Xcode to renew. TestFlight
and the App Store need the $99/year Apple Developer Program.

## Developing

- Node 22 is required by the Capacitor CLI (the web app itself builds on Node 20).
- After any web change: `npm run build && npx cap sync` copies `dist/` into both native projects.
- `npx cap open android` opens Android Studio (needs JDK 21).
- Icons and splash screens are generated from `app/assets/logo.png`:
  `npx @capacitor/assets generate --iconBackgroundColor "#000000" --splashBackgroundColor "#000000"`.
- Native-only code lives in `app/src/native.ts`: status bar styling, hiding the splash screen, and skipping the
  service worker, which only the website needs.
