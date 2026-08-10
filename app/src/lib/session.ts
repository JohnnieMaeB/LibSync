const SESSION_STORAGE_KEY = "libsync_session_id";

export function generateId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  // Fallback for browsers/test environments without crypto.randomUUID.
  return `sid-${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
}

export function getOrCreateSessionId(): string {
  let sessionId = localStorage.getItem(SESSION_STORAGE_KEY);
  if (!sessionId) {
    sessionId = generateId();
    localStorage.setItem(SESSION_STORAGE_KEY, sessionId);
  }
  return sessionId;
}
