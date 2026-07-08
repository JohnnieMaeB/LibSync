# LibSync — Tier 4: React Migration

Builds on [TIER1_PLAN.md](TIER1_PLAN.md) (real data, safe budget), [TIER2_PLAN.md](TIER2_PLAN.md) (AG-UI
streaming, tool-driven cards), and [TIER3_PLAN.md](TIER3_PLAN.md) (the component/token spec this migration
ports into code). Tier 4 is a **behavior-preserving framework migration** — no new user-facing features. The
payoff is structural: once this lands, Tiers 5–7 (standalone app, embeddable widget, mobile) all build on one
shared React component library instead of three divergent hand-rolled UIs.

---

## 1. Why now, why React specifically

This was flagged as a "worth exploring later" item back in Tier 3's discussion — the trigger condition was
"once Tier 2/3 land," and they now have. Two things make this the right moment, not a preference call:

1. **State complexity crossed a threshold.** Tier 3 alone specified streaming text, tool-status pills,
   multi-card types, a citation style switcher, copy-confirmation micro-states, and scroll-to-latest — that's
   real component state, not text-in/text-out DOM patching. Hand-rolled vanilla JS for this is exactly the
   kind of code that gets worse with every feature added, not better.
2. **The tooling isn't generic "React is nicer" — it's protocol-specific.** Tier 2 chose AG-UI because
   PydanticAI ships a first-party adapter. CopilotKit — the team that *built* AG-UI — ships React hooks
   (`useAgent`, `useCoAgent`) that consume that exact event stream, plus pre-built, CSS-theamble chat
   components (`CopilotChat`, `CopilotPopup`, `CopilotSidebar`) via `@copilotkit/react-ui`. Moving to React
   isn't a rewrite for its own sake — it's picking up the reference client for a protocol already in the
   stack.

**What this is not:** a UI redesign. Tier 3's visual spec is the target; Tier 4 is porting the existing
hand-rolled vanilla JS implementation of it into components, not changing what it looks like.

---

## 2. Key decisions

### 2.1 Build tool → Vite

**Why:** the standard, fastest-starting React build tool in 2026; zero-config TypeScript/JSX support; trivial
GitHub Pages deployment via `base` path config in `vite.config.ts` + a build step in CI.
**How:** `npm create vite@latest -- --template react-ts` inside a new `client/` structure (see §4).

### 2.2 Agent transport → CopilotKit + AG-UI

**Why:** reuses Tier 2's `AGUIAdapter` backend endpoint as-is — no backend changes. `useAgent`/`useCoAgent`
handle message streaming, tool-call events, and shared state without hand-rolled `fetch` + `ReadableStream`
parsing.
**How:** `@copilotkit/react-core` + `@copilotkit/react-ui`, pointed at the existing `/agent` AG-UI endpoint
from Tier 2 Phase 6. `CopilotChat` becomes the base for the main conversation view; custom render props handle
Tier 2/3's book/research/citation cards as generative-UI components tied to specific tool names.

### 2.3 Theming → CSS custom properties, not a rebuild

**Why:** Tier 3 already formalized LibSync's tokens (`--ls-bg`, `--ls-accent`, etc.). CopilotKit's own
component CSS reads from its own custom properties (e.g. `--copilot-kit-primary-color`).
**How:** map Tier 3's tokens onto CopilotKit's theming variables once, in a single theme file — the brand
carries over, it isn't reimplemented.

### 2.4 Testing → Vitest + React Testing Library

**Why:** Vite-native, faster and less config than Jest for a Vite project; same assertion API developers
already know from Jest.
**How:** replaces `client/src/script.test.js`'s Jest setup; component tests assert rendered output and
tool-event-driven card rendering, not DOM string manipulation.

### 2.5 Fix the `client/src` ↔ `docs/` drift for real this time

**Why:** Tier 1's audit flagged that these two copies are hand-duplicated and have already diverged; Tier 1
Phase 3 patched it with a sync script, but that's a discipline problem wearing a script's clothing — someone
still has to remember to run it. A build step makes drift structurally impossible instead of relying on that
discipline.
**How:** `docs/` becomes a **build artifact**, not a hand-edited source directory — a GitHub Actions workflow
runs `vite build` and publishes the output there (or to a dedicated `gh-pages` branch) on every push to `main`.
Nobody edits `docs/` by hand again.

---

## 3. Scope boundary

| In scope | Out of scope (later tiers) |
|---|---|
| Port existing chat UI + Tier 3's card designs to React components | Multi-conversation history / sidebar (→ Tier 5) |
| Wire CopilotKit/AG-UI transport | Dynamic/responsive full-app layout (→ Tier 5) |
| Vite build + CI deploy to GitHub Pages | Embeddable widget mode (→ Tier 6) |
| Vitest component tests | Mobile app packaging (→ Tier 7) |

---

## 4. Updated project structure

```
LibSync/
├── app/                     # NEW — Vite + React frontend (replaces client/src as source of truth)
│   ├── src/
│   │   ├── components/      # ChatWindow, BookCard, CitationCard, ResearchCard, ToolStatusPill, ...
│   │   ├── theme/           # CSS custom properties mapped from TIER3_PLAN.md's token spec
│   │   └── main.tsx
│   ├── vite.config.ts
│   └── package.json
├── docs/                    # Now a BUILD ARTIFACT — generated by CI, never hand-edited
├── client/src/              # Retired after cutover; kept one release for rollback, then removed
├── server/                  # Unchanged
└── planning/
```

---

## 5. Roadmap (continues Tier 1–3's phase numbering)

| Phase | Scope | Est. |
|---|---|---|
| **15** | Scaffold `app/` with Vite + React + TypeScript; port static markup/CSS 1:1 as plain components (no CopilotKit yet) — confirms the port is behavior-identical before adding new transport logic | 2–3 days |
| **16** | Wire `@copilotkit/react-core`/`react-ui` to the existing `/agent` AG-UI endpoint; replace the plain-component chat with `CopilotChat` + custom render props for Tier 2/3's cards | 4–6 days |
| **17** | Vitest + React Testing Library test suite covering component rendering and tool-event-driven card display | 2–3 days |
| **18** | CI cutover: GitHub Actions builds `app/` and publishes to `docs/`; retire hand-edited `client/src/`; update `README.md`'s project structure section | 1–2 days |

**Done when:** the live site is served from a CI-built React app, visually and behaviorally matching Tier 3's
spec, with `docs/` never hand-edited again.

---

## 6. Budget ledger addendum

| Item | Cost |
|---|---|
| Vite, React, TypeScript, Vitest, RTL | $0 — open source npm packages |
| `@copilotkit/react-core` / `react-ui` | $0 — open source, no CopilotKit Cloud account needed for the AG-UI transport itself |
| GitHub Actions build minutes | $0 — well within the free tier for a low-traffic repo |
| GitHub Pages hosting | $0 — unchanged from Tier 1 |

No new paid services. This tier is pure tooling/architecture — it should be invisible to the budget ledger.

---

## 7. Definition of done

- The live site runs on React + Vite, built and deployed by CI.
- Visual output matches Tier 3's spec exactly — this is a migration, not a redesign.
- `docs/` is generated, not hand-edited; the drift bug flagged in Tier 1/3 is structurally closed.
- Tool calls, streaming, and card rendering all go through CopilotKit's AG-UI bindings, not hand-rolled fetch/stream parsing.

Once this bar is met, [TIER5_PLAN.md](TIER5_PLAN.md) covers turning this into a full standalone app — dynamic
layout and multi-conversation history — on top of the component library this tier establishes.
