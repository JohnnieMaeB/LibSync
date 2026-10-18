import "@testing-library/jest-dom/vitest";
// jsdom doesn't implement IndexedDB; App now persists conversations to it
// (see app/src/lib/db.ts), so every test needs a working indexedDB global.
import "fake-indexeddb/auto";
import { configure } from "@testing-library/react";

// Text queries look at what's on screen; the screen-reader announcer
// (lib/announce.ts) repeats replies in a visually hidden status element and
// is tested on its own.
configure({ defaultIgnore: "script, style, .visually-hidden" });
