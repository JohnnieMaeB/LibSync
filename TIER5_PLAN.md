# LibSync — Tier 5: Standalone Web App

Builds on [TIER4_PLAN.md](TIER4_PLAN.md) (React + CopilotKit component library). Tier 5 turns LibSync from "a
chat widget sitting on a page" into a real destination app — the kind of dynamic, full-viewport experience
ChatGPT, Claude, and Gemini all have, including **multi-conversation history** (see §2, this is the direct
answer to "does any plan cover chat history navigation" — it didn't, until now).

---

## 1. What "static" actually means today, and why it's a problem

The live app is a fixed 420px-wide, 90vh-tall card centered on the page — deliberately a "widget" identity
(Tier 3 called this out as intentional and worth keeping *as an option*). But as the only way to use LibSync,
it reads as small and app-like-but-not-quite: no use of viewport space on desktop, no persistent place to
return to a previous conversation, no sense of "this is where I do my library research," just a box that
resets every time you reload.

Popular chat apps solve this with the same handful of patterns: a persistent sidebar for navigation and
history, a full-height/full-width main column, a collapsible sidebar on narrower viewports, and installability
(PWA) so the app feels like a destination, not a page.

---

## 2. Chat history — multi-conversation navigation

**This wasn't covered in Tiers 1–3.** Tier 1 Phase 3 added *session continuity within one conversation*
(`session_id → message_history`, so a single chat doesn't forget itself mid-conversation) — that's a different
problem from *multiple, named, revisitable conversations* the way ChatGPT/Claude's sidebar works. This tier
adds the latter as a first-class feature.

### Design

- **Storage: client-side, not server-side.** Render's free tier has no durable disk and the app has no
  accounts/auth — so conversations live in the browser via **IndexedDB** (not `localStorage`: better suited to
  structured, growing data, and not subject to `localStorage`'s ~5–10MB string-only ceiling).
- Each conversation is `{id, title, createdAt, updatedAt, messages[]}`. Title auto-generates from the first
  user message (truncated), editable by the user, matching the ChatGPT/Claude pattern.
- Sidebar lists conversations newest-first, click to switch, with rename/delete and a "New chat" action.
- **Architectural simplification this enables:** Tier 1 Phase 3 introduced a bounded in-memory server-side
  session dict; Tier 2 Phase 6 collapsed it onto AG-UI's thread id via `StateDeps`. Once the client reliably
  persists full message history here, that server-side thread state can be simplified further — the client
  sends the relevant history with each request instead of the server trying to remember it across a Render
  cold start. The server becomes closer to stateless per-request; the client is the durable store. This is a
  genuine improvement, not just a new feature bolted on top of an old stopgap.
- **Cross-device sync is explicitly out of scope.** That requires accounts and server-side storage — a real
  architectural addition, not a checkbox. [TIER8_PLAN.md](TIER8_PLAN.md) introduces exactly that (Supabase
  Postgres + Auth), but for library *staff* managing an instance, not patrons. Patron-side cross-device sync
  is its own deliberate decision, made in [TIER9_PLAN.md](TIER9_PLAN.md) — deferred there, not dropped.

---

## 3. Dynamic layout

Patterns adopted, matching current chat-app conventions:

| Element | Behavior |
|---|---|
| Sidebar | Persistent on desktop (≥1024px), collapsible to icon-only, becomes a slide-over drawer on mobile |
| Main column | Full viewport height, fluid width up to a comfortable max reading width (not stretched edge-to-edge on ultrawide) |
| Empty state | "New chat" view with Tier 3's suggestion chips, not a blank column |
| Keyboard shortcuts | `Cmd/Ctrl+K` — new chat (common convention across ChatGPT/Claude/Linear); `Esc` — close sidebar drawer on mobile |
| Breakpoints | Mobile (<640px): full-screen chat, drawer sidebar · Tablet (640–1024px): narrower fixed sidebar · Desktop (≥1024px): full layout |

The "widget" 420px card mode from before isn't deleted — it becomes an explicit compact mode, reused directly
by Tier 6's embeddable widget.

---

## 4. Installability (PWA)

**Why:** zero marginal cost, makes the app "installable" (Add to Home Screen / desktop app icon) without any
app-store presence — directly relevant groundwork for Tier 7's mobile question, and free.
**How:** a Web App Manifest (`manifest.json` — name, icons from the existing LibSync mark, theme color
`#ffd166`, background color `#000000`) plus a minimal service worker for static-asset caching (not full
offline chat — that needs the backend). GitHub Pages already serves over HTTPS, which is the only hard
requirement for installability.

**Platform note:** Android/Chrome shows a native "Install" prompt automatically; iOS Safari requires the user
to manually choose "Add to Home Screen" from the share sheet and has historically lagged on PWA feature parity
(push notifications, background sync) — document this honestly rather than promising iOS behaves identically
to Android.

---

## 5. Roadmap (continues Tier 1–4's phase numbering)

| Phase | Scope | Est. |
|---|---|---|
| **19** | Dynamic layout shell: sidebar + main column, breakpoints, collapsible/drawer behavior | 3–5 days |
| **20** | Chat history engine: IndexedDB schema, conversation CRUD, sidebar list UI, title auto-generation | 4–6 days |
| **21** | Simplify the AG-UI thread state from Tier 1 Phase 3 / Tier 2 Phase 6 now that the client is the durable store (see §2) | 1–2 days |
| **22** | PWA installability: manifest, icons, service worker for static assets, keyboard shortcuts | 2–3 days |

**Done when:** a user can hold multiple named conversations, switch between them, reload the page without
losing any of them, and install the app to their home screen/desktop.

---

## 6. Budget ledger addendum

| Item | Cost |
|---|---|
| IndexedDB | $0 — native browser API |
| Web App Manifest + service worker | $0 — native browser features |
| No new backend infrastructure | Server-side session store gets *simpler*, not more expensive |

---

## 7. Definition of done

- Multiple named conversations exist, are listed in a sidebar, and are switchable without losing state.
- The layout is genuinely responsive — not just a resized version of the fixed widget card.
- The app is installable as a PWA on both desktop and Android; iOS's manual "Add to Home Screen" path works and its limitations are documented, not hidden.
- Still $0/month — no new paid infrastructure.

Once this bar is met, [TIER6_PLAN.md](TIER6_PLAN.md) covers packaging the same component library as an
embeddable widget for library websites, and [TIER7_PLAN.md](TIER7_PLAN.md) covers wrapping this app for iOS
and Android.
