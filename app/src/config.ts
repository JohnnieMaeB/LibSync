// Single source of truth for the backend API base URL. Same hardcoded Render
// URL as the pre-migration client/src/config.js, now overridable via Vite's
// VITE_API_BASE_URL env var for local dev against a different backend.
export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL || "https://libsync.onrender.com";
