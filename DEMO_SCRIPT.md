# LibSync — Demo Script

A scripted conversation flow that exercises every working Tier 1 + Tier 2 capability, presented through the
Tier 3 UI, in order, so you can recreate the full demo reliably (for yourself, in an interview, or on a
call). Each turn says what to type, what it's testing, and what a correct answer looks like so you can tell
"working" from "broken" at a glance.

This assumes the seed policy data from [`pinecone-scripts/upsert_pinecone_records.py`](pinecone-scripts/upsert_pinecone_records.py)
is already loaded (see [README §2](README.md#-local-setup)) and the server is running with real
`GROQ_API_KEY` / `PINECONE_API_KEY` values. `OPENALEX_MAILTO` / `CROSSREF_MAILTO` are optional but
recommended for Turns 6–7 (see [README's env var section](README.md#-local-setup)) — the research and
citation tools work without them, just in each API's slower anonymous rate-limit pool.

---

## Before you start

- **Server running:** `cd server && uv run uvicorn app.main:app --reload --port 3000`
- **Frontend open:** `client/src/index.html` in a browser, pointed at your server (see
  [README §5](README.md#-local-setup)) — or the [live GitHub Pages demo](https://johnniemaeb.github.io/LibSync/)
  against the deployed Render backend.
- **Optional but recommended:** [Logfire](https://logfire.pydantic.dev/) dashboard open in another tab if
  `LOGFIRE_TOKEN` is set — you can watch each tool call (`search_library_policies`, `search_catalog`,
  `search_scholarly_works`, `lookup_and_cite`) fire in real time as you go through the script, which is a
  good visual for a demo. You'll also see it live in the chat itself: the bot bubble shows a tool-specific
  status pill (e.g. "🔍 Searching the catalog") the moment a tool call starts, streamed over the AG-UI
  transport (`POST /agent`) — no blank spinner.
- **Fresh session:** clear the site's `localStorage` (or open a private/incognito window) so turn 1 starts
  a brand-new thread id and the continuity turns later actually prove something.

---

## What Tier 3 adds to this walkthrough

The turns below are unchanged from Tier 1/2 — same questions, same grounded data — but the UI around them
now demonstrates its own things worth calling out during a demo:

- **Suggestion chips** on first load (before turn 1): four starter prompts under the intro bubble, gone
  after the first message is sent.
- **Tool-status pills** are now tool-specific ("🔍 Searching the catalog", "🎓 Looking up research", "🎓
  Looking up citation", "📚 Checking library policies"), not a generic "Searching…".
- **Stop button:** the Send button becomes a red "Stop" control the instant any turn is submitted — even
  before "Thinking…" resolves into a tool call or text. Click it mid-turn to interrupt a request; the bubble
  finalizes as "Stopped." with a Regenerate action, no dangling state.
- **Grounded in N sources:** any reply backed by one or more cards (turns 5–7) gets a small tag plus a
  numbered badge on each card — the visible payoff of Tier 2's retrieval work.
- **Copy / Regenerate:** hover (or Tab-focus) any bot reply to reveal a Copy button; only the most recent
  reply also shows Regenerate, which re-runs the same question without duplicating your message in the
  transcript.
- **Retry on error:** simulate a failure (stop the server mid-request, or see Turn 12 below) and the error
  bubble shows a Retry button that resubmits the same question — good for demonstrating recovery without
  retyping.
- **Keyboard/screen-reader pass:** Tab through chips → input → Send/Stop → message actions to show visible
  focus rings; the chat region is `role="log" aria-live="polite"` so a screen reader announces new replies.

---

## The script

### Turn 1 — Baseline persona (no tool call)

> **Type:** `Hi there!`

Expect a friendly, in-character greeting — enthusiastic "digital navigator" persona, no policy or book
data involved. This one should stream in fast since it's plain text with no tool call round trip.

**Confirms:** the agent, system prompt, and AG-UI streaming pipe all work before anything data-dependent is
tested.

---

### Turn 2 — Policy question, grounded in Pinecone (fines)

> **Type:** `How much are late fees?`

Expect a grounded answer citing **$0.25/day**, capped at **$5.00 per item** (from `pol3` and `pol11` in the
seed data). If Logfire is open, you should see a `search_library_policies` tool call with `"late fees"` (or
similar) as the query, and the Pinecone match(es) it returned.

**Confirms:** RAG is real — the number in the reply must match the seed data exactly, not a plausible-sounding invented number.

---

### Turn 3 — Policy question, different category (facilities)

> **Type:** `Can I book a meeting room?`

Expect grounding in `pol5` / `pol22` — non-commercial use, two hours per group per week, 48 hours advance
notice, inquire at the front desk.

**Confirms:** retrieval isn't a fluke — a second, unrelated category also grounds correctly.

---

### Turn 4 — Policy question, a less obvious category (accessibility)

> **Type:** `Do you have anything for people with visual impairments?`

Expect grounding in `pol31` — assistive technology (screen readers, large-print keyboards) available on
request at any public computer station.

**Confirms:** retrieval covers the full seed set (34 records across 8 categories), not just the first few.

---

### Turn 5 — Book question, real Open Library data + a live card

> **Type:** `Is Project Hail Mary by Andy Weir available?`

Watch the bot bubble show a **"🔍 Searching the catalog"** status pill the moment `search_catalog` fires, then expect a real **book
card** — cover thumbnail (when Open Library has one), the title linked out to the book's Open Library page,
author, and an availability badge (often `unknown`, which is a real, honest status from Open Library's
Availability API — not every edition is in the Internet Archive lending program — see
[ARCHITECTURE.md](ARCHITECTURE.md)). The card renders live, as soon as the tool call resolves, and any
narration the model adds appears alongside it, not replacing it. A small numbered badge on the card and a
"Grounded in 1 source" tag above the reply are Tier 3 additions — the same numbering scheme extends to
turns 6 and 7 whenever a reply is backed by more than one card.

If Logfire is open, you should see a `search_catalog` tool call, followed by an HTTP call out to
`openlibrary.org`.

**Confirms:** the catalog tool hits the real Open Library API, the card renders from a live `CUSTOM`
event on the AG-UI stream (not parsed out of prose), text/cards coexist correctly regardless of which
arrives first, and the grounding tag/badge accurately reflects how many sources backed the reply.

---

### Turn 6 — Research question, real OpenAlex data (new in Tier 2)

> **Type:** `Find recent papers on large language models in education`

Expect a **research result card**: real paper titles, authors, publication year, a citation-count badge,
and an open-access badge — for example "ChatGPT for good? On opportunities and challenges of large language
models for education" (Kasneci et al., 2023, thousands of citations, open access). Click **"▸ Abstract"** on
any entry to expand a real abstract reconstructed from OpenAlex's data.

If Logfire is open, you should see a `search_scholarly_works` tool call, followed by an HTTP call out to
`api.openalex.org`.

**Confirms:** the research assistant hits the real OpenAlex API and never invents a paper, author, or
citation count — everything in the card is traceable to a live API response.

---

### Turn 7 — Citation request, real Crossref + citeproc-py formatting (new in Tier 2)

> **Type:** `Give me an MLA citation for DOI 10.1016/j.lindif.2023.102274`

Expect a **citation card**: a real MLA-formatted citation (author, title, journal, volume, date, DOI link),
a **Copy** button, and a style switcher (APA/MLA/Chicago). Switch the dropdown to a different style — the
citation text updates **instantly**, without a new "thinking" round trip, because the switcher calls
`GET /citation/{doi}` directly rather than re-running the whole tool.

If Logfire is open, you should see a `lookup_and_cite` tool call, followed by an HTTP call out to
`api.crossref.org`.

**Confirms:** the citation is grounded in a real Crossref bibliographic record and formatted by the actual
CSL 1.0.1 processor (`citeproc-py`), not a model recalling style rules from memory — and the style switcher
doesn't re-resolve Crossref for every click.

---

### Turn 8 — Multi-turn continuity (no title repeated)

> **Type:** `What's it about?`

Don't restate the title — the agent should still know you mean *Project Hail Mary* from the conversation
history.

**Confirms:** the thread id + the server-side session store are threading conversation context correctly
across turns, over the AG-UI transport.

---

### Turn 9 — Honesty boundary (a platform the agent can't actually check)

> **Type:** `Can you check if it's available on Libby right now?`

Expect the agent to clarify it **can't** check real-time Libby/OverDrive availability (no public API exists
for that), while still being helpful about *how* you'd check it yourself in the Libby app. It should not
invent a "yes, it's available" or "no holds" answer.

**Confirms:** the system prompt's explicit honesty guardrail around commercial platforms is holding — this
is the exact failure mode Tier 1 was built to eliminate (see
[TIER1_PLAN.md §1](TIER1_PLAN.md#1-where-the-project-actually-is-today)).

---

### Turn 10 — No-match question (honest "I don't know")

> **Type:** `Do you offer piano lessons?`

Expect the agent to say it doesn't have that information rather than fabricating a policy. Nothing in the
seed data covers piano lessons, so `search_library_policies` should come back empty or irrelevant.

**Confirms:** the agent doesn't hallucinate a policy when retrieval genuinely finds nothing relevant.

---

### Turn 11 — Session reset (proves the $0-cost tradeoff, not a bug)

Open a **new private/incognito window** (fresh `localStorage`, so a new thread id is minted) and type:

> **Type:** `What did I just ask you?`

Expect the agent to have **no memory** of turns 1–10 — this is a fresh session. This is the documented,
intentional tradeoff from not running a database (see
[README's live-demo note](README.md#-featured-deployment) and
[TIER1_PLAN.md §2.4](TIER1_PLAN.md#24-session-continuity-without-a-database)), not something to "fix."

**Confirms:** session boundaries are respected — conversations don't leak across sessions.

---

## Verifying at the wire level (no browser needed)

To sanity-check the backend directly, or capture raw AG-UI SSE output for a demo, `POST /agent` with a
minimal [`RunAgentInput`](https://docs.ag-ui.com/) body — `threadId`/`runId` can be any string you mint
yourself (e.g. `uuidgen` or just a fixed test value):

```bash
curl -sN -X POST http://localhost:3000/agent \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "threadId": "demo-thread-1",
    "runId": "demo-run-1",
    "state": null,
    "messages": [{"id": "m1", "role": "user", "content": "How much are late fees?"}],
    "tools": [], "context": [], "forwardedProps": null
  }'
```

You should see, in order: `RUN_STARTED`, one or more `TEXT_MESSAGE_START`/`TEXT_MESSAGE_CONTENT` frames
(cumulative text deltas), possibly `TOOL_CALL_START`/`TOOL_CALL_ARGS`/`TOOL_CALL_END`/`TOOL_CALL_RESULT`
around a tool call, a `CUSTOM` event for any card (book/research/citation), then `RUN_FINISHED`. A
`RUN_ERROR` event instead means the turn failed — see Troubleshooting below.

To continue the same conversation from the command line, reuse the same `threadId` — the server threads
history through its session store keyed by thread id, so you only need to send the new turn:

```bash
curl -sN -X POST http://localhost:3000/agent \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "threadId": "demo-thread-1",
    "runId": "demo-run-2",
    "state": null,
    "messages": [{"id": "m2", "role": "user", "content": "What about the audiobook?"}],
    "tools": [], "context": [], "forwardedProps": null
  }'
```

To exercise the research and citation tools directly:

```bash
curl -sN -X POST http://localhost:3000/agent \
  -H "Content-Type: application/json" -H "Accept: text/event-stream" \
  -d '{"threadId":"demo-research","runId":"r1","state":null,"messages":[{"id":"m1","role":"user","content":"Find recent papers on large language models in education"}],"tools":[],"context":[],"forwardedProps":null}'

curl -sN -X POST http://localhost:3000/agent \
  -H "Content-Type: application/json" -H "Accept: text/event-stream" \
  -d '{"threadId":"demo-citation","runId":"r1","state":null,"messages":[{"id":"m1","role":"user","content":"Cite DOI 10.1016/j.lindif.2023.102274 in APA"}],"tools":[],"context":[],"forwardedProps":null}'
```

And the citation style switcher directly (no tool call, no LLM round trip — just Crossref + citeproc-py):

```bash
curl -s "http://localhost:3000/citation/10.1016/j.lindif.2023.102274?style=chicago"
```

The older `/chat` and `/chat/stream` endpoints (plain JSON / a bespoke `event: text` / `event: books` /
`event: done` SSE contract) still work exactly as in Tier 1, if you want to verify the fallback transport:

```bash
curl -sN -X POST http://localhost:3000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"How much are late fees?"}'
```

---

## Known quirks (not bugs)

- **Book answers sometimes come back as prose instead of a card, especially in a continued conversation.**
  If the model answers a follow-up from context instead of re-calling `search_catalog` (e.g. repeating a
  question already answered earlier in the same session), no new `book_card` event fires — you'll get a
  grounded text answer instead of a live card. Both are correct, grounded answers; only the presentation
  differs. Ask a fresh, specific book question in a new session to reliably see the card.
- **A retry pause, or occasionally a `RUN_ERROR` event, if you run through this script very quickly several
  times in a row.** Groq's free tier is 30 requests/minute — rapid-fire demo re-runs can trip it. Space out
  repeated full run-throughs by a minute or so.
- **`availability: "unknown"`** on a book card is a real status from Open Library's Availability API (not
  every edition is in the Internet Archive lending program), not a broken lookup.
- **Citation formatting has minor real quirks of its own** (e.g. `citeproc-py`'s APA output can render
  `"Author, A.& Author, B.."` — a double period, missing a space before `&`). This is the actual CSL
  processor's real output, not a LibSync bug — see the golden-file tests in
  [`server/tests/test_citation_service.py`](server/tests/test_citation_service.py) for what's pinned as
  expected today.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Every reply is the generic "Unable to reach AI service" error | `GROQ_API_KEY` or `PINECONE_API_KEY` missing/invalid | Check `server/.env` against `server/.env.example`; see [README §2](README.md#-local-setup) |
| Server crashes on startup | Set `LOGFIRE_TOKEN` without the matching extra installed | Run `uv sync` in `server/` — `pyproject.toml` pins `logfire[fastapi]` |
| Logfire shows `401 Unauthorized` / `Failed to export span batch` in logs | Used a Logfire read token instead of a write token | Regenerate under **Settings → Write tokens**; see [README's Logfire setup steps](README.md#-local-setup) |
| Every request to `/agent` (or `/chat`) returns a CORS/network error in the browser console, even though `curl` against it works | `LOGFIRE_TOKEN` set with a `fastapi` version `>=0.137` — a known upstream `opentelemetry-instrumentation-fastapi` incompatibility 500s every CORS preflight | Confirm `fastapi<0.137` is pinned in `server/pyproject.toml` (it is, by default) and re-run `uv sync`; see [ARCHITECTURE.md's `fastapi<0.137` entry](ARCHITECTURE.md#why-these-choices) |
| Policy answers cite the wrong number or say "no information found" | Seed data not upserted yet | Run `pinecone-scripts/upsert_pinecone_records.py` (see [README §2](README.md#-local-setup)) |
| Book question never calls `search_catalog`, or a `RUN_ERROR` right after a stalling "Let me check..." text | A transient Groq tool-calling quirk, mitigated in code (`ModelRetry` + `run_stream_events()`, see [ARCHITECTURE.md](ARCHITECTURE.md)) | Retry the same question — if it fails consistently across many attempts, check the server logs for the real exception |
| Research/citation questions reply "temporarily unavailable" | OpenAlex or Crossref transiently unreachable, or rate-limited (more likely without `OPENALEX_MAILTO`/`CROSSREF_MAILTO` set) | Retry after a moment; set the polite-pool env vars (see [README §2](README.md#-local-setup)) if it happens often |
| Citation style switcher does nothing when you change the dropdown | Network hiccup on the `GET /citation/{doi}` call — the frontend intentionally leaves the previous text in place rather than showing an error for this low-stakes action | Retry the style switch; check the browser Network tab for the actual response if it persists |
