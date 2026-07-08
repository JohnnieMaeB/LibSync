# LibSync — Tier 3: UI/UX Enhancement Plan

Builds on [TIER1_PLAN.md](TIER1_PLAN.md) (Tier 1: real data, safe budget) and
[TIER2_PLAN.md](TIER2_PLAN.md) (Tier 2: AG-UI streaming, interactive book/research/citation cards). Tier 3
touches **no backend logic** — it's entirely about how those capabilities are presented. The brand stays
exactly as shipped: black ground, amber-gold accent, the circular glowing LibSync mark. This formalizes and
extends that identity; it does not re-skin it.

---

## 1. Brand audit — what's actually there today

Pulled directly from `client/src/styles/style.css`, `index.html`, and `assets/logo.png`:

| Token | Current value | Role |
|---|---|---|
| Page background | `#121212` | body |
| Container background | `#000000` | chat card |
| Accent | `#ffd166` (hover `#ffe066`) | header title, send button, container glow |
| Bot bubble | `#2a2a2a` | assistant messages |
| User bubble | `#3b3b3b` | user messages |
| Border | `#333` | header/footer dividers |
| Muted text | `#aaa` | tagline, secondary text |
| Type | `'Segoe UI', Tahoma, Geneva, Verdana, sans-serif` | all text |
| Logo | circular mark, black ground, amber glow, open book + sync arrows, "LibSync" wordmark baked in | header |

The container is a fixed 420px-wide, 90vh-tall rounded card centered on the page with an amber outer glow —
a deliberate "chat widget" identity, not a full-bleed app shell. Keep it.

### Bugs found during the audit (not style opinions — actual defects)

- **`index.html:7`** links `fonts.googleapis.com/css2?family=Segoe+UI` — Segoe UI is a Microsoft system font,
  not hosted on Google Fonts. This request 404s silently on every page load; the page has always been
  falling back to the OS's Segoe UI (Windows) or whatever generic sans the browser picks (Mac/Linux). Dead
  weight — remove it. Bonus: one fewer third-party request from the real product (unlike planning docs, this
  one ships to users).
- **`script.js` `appendMessage()`** sets `msg.innerHTML = text` directly on model output. Model output is
  untrusted — it can echo retrieved text or be steered via prompt injection — so this is a live HTML/script
  injection path, not just "no markdown support." Nothing in Tier 3's richer message content (bold, links,
  citation markers) is safe to add until this is replaced with an escape-by-default renderer.
- No `:focus-visible` styling anywhere — keyboard users get no visible focus indicator on the input or send button.
- `#chatBox` has no `role="log"` / `aria-live` — screen readers are never told a new message arrived.
- No semantic color exists for error/success/info states — only the brand accent. The current error message
  is styled identically to a normal bot bubble.

---

## 2. Framework: four properties, plus one LibSync-specific

Industry framing for what separates a good assistant UI from a bad one, used to structure this plan:

1. **Capability transparency** — can the user tell what the bot can do before typing?
2. **Recovery patterns** — what happens when generation fails or is wrong?
3. **Confidence / grounding display** — does the UI show when the bot is *sure*, and why?
4. **Accessibility** — does it work on mobile, with a screen reader, on keyboard only?
5. **Card fidelity** *(LibSync-specific, added for Tier 3)* — Tier 2 introduced book/research/citation cards; they need the same design attention as the chat bubbles do.

---

## 3. What other assistants do that's worth adopting

| Pattern | Seen in | LibSync adaptation |
|---|---|---|
| Streaming with a stop button | ChatGPT, Claude, Gemini | Send button swaps to an amber stop icon while a response streams |
| Numbered inline citations → expandable source card | Perplexity | Pinecone/Crossref/OpenAlex-grounded replies get `[1]`-style markers linking to a source card |
| Suggested-prompt chips on first load | ChatGPT, Claude | Four library-flavored starter chips under the intro bubble |
| Tool-status pill ("Searching…") | ChatGPT, Claude, Perplexity | Small pill above the bubble while a Tier 2 tool call is in flight, sourced from AG-UI `TOOL_CALL_START`/`RESULT` events |
| Message actions on hover (copy, regenerate) | All major assistants | Icon row under each bot bubble |
| Scroll-to-latest floating button | Slack, Discord, ChatGPT | Appears once the user scrolls up mid-reply instead of yanking them back down |

---

## 4. Design system (tokens, formalized — not changed)

```css
:root{
  --ls-bg:#121212;
  --ls-surface:#000000;
  --ls-bubble-bot:#2a2a2a;
  --ls-bubble-user:#3b3b3b;
  --ls-border:#333;
  --ls-text:#f0f0f0;
  --ls-text-muted:#aaa;
  --ls-accent:#ffd166;
  --ls-accent-hover:#ffe066;

  /* new — semantic states the current CSS has no vocabulary for */
  --ls-danger:#e8735c;
  --ls-success:#7cc48f;
  --ls-info:#7fb3d9;

  --ls-font: "Segoe UI", system-ui, -apple-system, "Helvetica Neue", Arial, sans-serif;
}
```

The font stack gains generic fallbacks (`system-ui`, `-apple-system`) so Mac/Linux users get a real system
sans instead of an arbitrary browser default — the brand's typographic *feel* (clean system UI face) survives
even where literal Segoe UI doesn't exist. No new typeface is introduced.

---

## 5. Feature-by-feature plan, by property

### Capability transparency
- Suggested-prompt chips on first load: e.g. *"Find me a sci-fi audiobook," "How do I renew a book?," "Cite this paper in APA," "What are your library card policies?"* — teaches the assistant's range (Tier 1 policies, Tier 2 catalog/research/citation) without a manual.
- Tool-status pill surfacing live tool activity: "🔍 Searching the catalog…", "📚 Checking library policies…", "🎓 Looking up citation…" — makes Tier 2's tool-calling visible instead of a silent pause.
- One dismissible "what I can do" line near the header — not a full onboarding tour.

### Recovery patterns
- Distinct error-bubble style using `--ls-danger`, with an inline retry button that resubmits the last message.
- Stop-generating control during streaming (depends on Tier 2's AG-UI stream being cancellable).
- Regenerate action on the most recent bot message.

### Confidence / grounding display
- Numbered inline citation markers in any reply that used Pinecone, Crossref, or OpenAlex, linking to an expandable source card (title, snippet, link) below the message — gives Tier 2's "reduce hallucination" retrieval work a visible payoff instead of leaving it invisible in the backend.
- A small "grounded in N sources" tag under retrieval-backed replies.

### Accessibility
- `role="log" aria-live="polite"` on the chat region.
- Visible focus rings (`--ls-accent`) on every interactive element: input, send/stop, suggestion chips, card buttons.
- `prefers-reduced-motion` handling for the streaming cursor, typing dots, and card entrance animation.
- Safe-markdown rendering replacing raw `innerHTML` — closes the injection gap *and* finally renders bold/links/lists instead of literal asterisks.
- Keyboard-operable cards: Tab to focus, Enter/Space to expand.

### Card fidelity (Tier 2's visual payoff)
- **Book card:** cover thumbnail, title/author, availability badge (`--ls-success`/`--ls-danger`/`--ls-info` by status), "View on Open Library" link, hover glow that echoes the logo's own amber halo.
- **Research card:** ranked list, open-access badge, expandable abstract.
- **Citation card:** formatted citation text, an APA/MLA/Chicago style-switcher, copy button with a micro "Copied ✓" confirmation.

---

## 6. Roadmap (continues Tier 1/2's phase numbering)

| Phase | Scope | Est. |
|---|---|---|
| **10** | Design system formalization: tokens, safe-markdown renderer (closes the XSS gap), a11y baseline (focus states, `aria-live`, reduced-motion), remove the dead font link | 2–3 days |
| **11** | Conversational affordances: suggestion chips, tool-status pills, stop/regenerate, scroll-to-latest | 3–4 days |
| **12** | Grounding & citations UI: inline citation markers + expandable source cards, "grounded in N sources" tag — depends on Tier 2 Phases 7–8 | 3–5 days |
| **13** | Card visual system: final book/research/citation card spec + micro-interactions, keyboard operability | 3–5 days |
| **14** *(superseded — see note)* | Responsive desktop layout: widen beyond the 420px widget shell on larger viewports without abandoning the mobile "widget" identity | 2–3 days |

> **Phase 14 update:** superseded by [TIER5_PLAN.md](TIER5_PLAN.md) Phase 19, which does this properly as part
> of turning LibSync into a full standalone app (sidebar, breakpoints, chat history) rather than just widening
> the widget card. Left here for history; don't build it twice.

---

## 7. Budget ledger addendum

No new services, no new dependencies with a cost surface — this tier is CSS, a safe-markdown renderer, and
accessibility/interaction work on the existing frontend. $0 impact, not because it was optimized down to $0,
but because there was never anything here that could cost money.

---

## 8. Definition of done for Tier 3

- Model output can never inject raw HTML/script — it renders through a safe path, always.
- Every interactive element has a visible keyboard focus state; the chat region is announced to screen readers.
- A reply that used retrieval visibly shows its sources — not just a paragraph of confident-sounding prose.
- Streaming responses can be stopped mid-generation; a failed request looks visually distinct from a normal reply and offers retry.
- The brand — black ground, amber accent, the LibSync mark — is unchanged. Everything above is addition, not a redesign.

Once this bar is met, [TIER4_PLAN.md](TIER4_PLAN.md) covers porting this component/token spec into a React
codebase — the foundation [TIER5](TIER5_PLAN.md), [TIER6](TIER6_PLAN.md), and [TIER7](TIER7_PLAN.md) build on
for the standalone app, embeddable widget, and mobile apps.
