// Single source of truth for the backend API base URL. Loaded before
// script.js via a <script> tag, so script.js can reference API_BASE_URL
// directly (classic scripts share one global scope) — this file also
// exports it for Node/Jest, where each require()'d file gets its own scope.
const API_BASE_URL = "https://libsync.onrender.com";

if (typeof globalThis !== "undefined") {
  globalThis.API_BASE_URL = API_BASE_URL;
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { API_BASE_URL };
}
