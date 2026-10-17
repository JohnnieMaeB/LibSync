import { API_BASE_URL } from "./config";
import type { ConversationSync } from "./hooks/useConversations";
import type { Conversation } from "./types";

// Tier 9 Phase 36: an optional patron session. The token is opaque (encrypted
// and signed by the backend); it holds no PIN, and nothing in it is readable
// here. Kept in localStorage so it survives a reload; it expires after 12 hours.

export interface PatronSession {
  token: string;
  kind: "card" | "email";
  libraryId: string;
  expiresAt: number;
}

const STORAGE_KEY = "libsync:patron";

export function loadSession(libraryId: string | null): PatronSession | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const session = JSON.parse(raw) as PatronSession;
    if (session.libraryId !== libraryId || session.expiresAt * 1000 < Date.now()) return null;
    return session;
  } catch {
    return null;
  }
}

function saveSession(body: { token: string; kind: "card" | "email"; library_id: string; expires_at: number }) {
  const session: PatronSession = {
    token: body.token,
    kind: body.kind,
    libraryId: body.library_id,
    expiresAt: body.expires_at,
  };
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  } catch {
    // Private mode: the session lasts until the page closes.
  }
  return session;
}

export function signOut() {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* nothing stored */
  }
}

async function post(path: string, libraryId: string, body: unknown) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-LibSync-Library": libraryId },
    body: JSON.stringify(body),
  });
  const json = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(json.detail ?? "Something went wrong. Try again.");
  return json;
}

export async function signInWithCard(libraryId: string, card: string, pin: string): Promise<PatronSession> {
  return saveSession(await post("/patron/sign-in/card", libraryId, { card, pin }));
}

export async function requestEmailLink(libraryId: string, email: string): Promise<void> {
  const redirectTo = `${window.location.origin}${window.location.pathname}${window.location.search}`;
  await post("/patron/email-link", libraryId, { email, redirect_to: redirectTo });
}

// The magic link lands back here with the Supabase session in the URL fragment
// (#access_token=…&type=magiclink). Exchange it for a LibSync session, then
// remove it from the address bar so it isn't bookmarked or shared.
export async function consumeMagicLink(libraryId: string | null): Promise<PatronSession | null> {
  const params = new URLSearchParams(window.location.hash.replace(/^#/, ""));
  const accessToken = params.get("access_token");
  if (!accessToken || !libraryId) return null;
  window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}`);
  try {
    return saveSession(await post("/patron/sign-in/email", libraryId, { access_token: accessToken }));
  } catch {
    return null;
  }
}

// Tier 9 Phase 37: the server side of a signed-in patron's history.
export function conversationSync(session: PatronSession): ConversationSync {
  const base = `${API_BASE_URL}/patron/conversations`;
  const headers = { "X-LibSync-Patron": session.token };
  async function check(response: Response) {
    if (!response.ok) throw new Error(`sync failed (${response.status})`);
    return response;
  }
  return {
    async pull() {
      return (await check(await fetch(base, { headers }))).json() as Promise<Conversation[]>;
    },
    async push(conversation) {
      const { id, title, createdAt, updatedAt, entries } = conversation;
      await check(
        await fetch(`${base}/${encodeURIComponent(id)}`, {
          method: "PUT",
          headers: { ...headers, "Content-Type": "application/json" },
          body: JSON.stringify({ title, createdAt, updatedAt, entries }),
        }),
      );
    },
    async remove(id) {
      await check(await fetch(`${base}/${encodeURIComponent(id)}`, { method: "DELETE", headers }));
    },
  };
}
