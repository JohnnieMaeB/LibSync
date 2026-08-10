import "@testing-library/jest-dom/vitest";
// jsdom doesn't implement IndexedDB; App now persists conversations to it
// (see app/src/lib/db.ts), so every test needs a working indexedDB global.
import "fake-indexeddb/auto";
