# LibSync — Demo Script

A scripted conversation flow that exercises every working Tier 1 capability, in order, so you can
recreate the full demo reliably (for yourself, in an interview, or on a call). Each turn says what to
type, what it's testing, and what a correct answer looks like so you can tell "working" from "broken" at
a glance.

This assumes the seed policy data from [`pinecone-scripts/upsert_pinecone_records.py`](pinecone-scripts/upsert_pinecone_records.py)
is already loaded (see [README §2](README.md#-local-setup)) and the server is running with real
`GROQ_API_KEY` / `PINECONE_API_KEY` values.

---

## Before you start

- **Server running:** `cd server && uv run uvicorn app.main:app --reload --port 3000`
- **Frontend open:** `client/src/index.html` in a browser, pointed at your server (see
  [README §5](README.md#-local-setup)) — or the [live GitHub Pages demo](https://johnniemaeb.github.io/LibSync/)
  against the deployed Render backend.
- **Optional but recommended:** [Logfire](https://logfire.pydantic.dev/) dashboard open in another tab if
  `LOGFIRE_TOKEN` is set — you can watch each `search_library_policies` / `search_catalog` tool call fire
  in real time as you go through the script, which is a good visual for a demo.
- **Fresh session:** clear the site's `localStorage` (or open a private/incognito window) so turn 1 starts
  a brand-new `session_id` and the continuity turns later actually prove something.

---

## The script

### Turn 1 — Baseline persona (no tool call)

> **Type:** `Hi there!`

Expect a friendly, in-character greeting — enthusiastic "digital navigator" persona, no policy or book
data involved. This one should stream in fast since it's plain text with no tool call round trip.

**Confirms:** the agent, system prompt, and streaming pipe all work before anything data-dependent is
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

### Turn 5 — Book question, real Open Library data + structured output

> **Type:** `Is Project Hail Mary by Andy Weir available?`

Expect either:
- A **structured book result card** — title "Project Hail Mary (2021)", author "Andy Weir", an availability
  badge (often `unknown`, which is a real, honest status from Open Library's Availability API, not a bug —
  see [ARCHITECTURE.md](ARCHITECTURE.md)), or
- The same information as well-formatted prose (the model doesn't *always* choose the structured path —
  both are correct, grounded answers; see the "known quirks" note below).

If Logfire is open, you should see a `search_catalog` tool call, followed by an HTTP call out to
`openlibrary.org`.

**Confirms:** the catalog tool hits the real Open Library API and the reply is grounded in what it
returned, not invented.

---

### Turn 6 — Multi-turn continuity (no title repeated)

> **Type:** `What's it about?`

Don't restate the title — the agent should still know you mean *Project Hail Mary* from the conversation
history.

**Confirms:** `session_id` + the server-side message history store are threading conversation context
correctly across turns.

---

### Turn 7 — Honesty boundary (a platform the agent can't actually check)

> **Type:** `Can you check if it's available on Libby right now?`

Expect the agent to clarify it **can't** check real-time Libby/OverDrive availability (no public API exists
for that), while still being helpful about *how* you'd check it yourself in the Libby app. It should not
invent a "yes, it's available" or "no holds" answer.

**Confirms:** the system prompt's explicit honesty guardrail around commercial platforms is holding — this
is the exact failure mode Tier 1 was built to eliminate (see
[TIER1_PLAN.md §1](TIER1_PLAN.md#1-where-the-project-actually-is-today)).

---

### Turn 8 — No-match question (honest "I don't know")

> **Type:** `Do you offer piano lessons?`

Expect the agent to say it doesn't have that information rather than fabricating a policy. Nothing in the
seed data covers piano lessons, so `search_library_policies` should come back empty or irrelevant.

**Confirms:** the agent doesn't hallucinate a policy when retrieval genuinely finds nothing relevant.

---

### Turn 9 — Session reset (proves the $0-cost tradeoff, not a bug)

Open a **new private/incognito window** (fresh `localStorage`, so a new `session_id` is minted) and type:

> **Type:** `What did I just ask you?`

Expect the agent to have **no memory** of turns 1–8 — this is a fresh session. This is the documented,
intentional tradeoff from not running a database (see
[README's live-demo note](README.md#-featured-deployment) and
[TIER1_PLAN.md §2.4](TIER1_PLAN.md#24-session-continuity-without-a-database)), not something to "fix."

**Confirms:** session boundaries are respected — conversations don't leak across sessions.

---

## Verifying at the wire level (no browser needed)

To sanity-check the backend directly, or capture raw SSE output for a demo:

```bash
curl -sN -X POST http://localhost:3000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"How much are late fees?"}'
```

You should see, in order: `event: session` (with a minted `session_id`), one or more `event: text` frames
with growing cumulative text (or a single `event: books` frame for a structured catalog answer), then
`event: done`. An `event: error` frame instead of `done` means the turn failed — see Troubleshooting below.

To continue the same session from the command line, pass the `session_id` from the first response back in:

```bash
curl -sN -X POST http://localhost:3000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"What about the audiobook?","session_id":"<paste session_id here>"}'
```

---

## Known quirks (not bugs)

- **Book answers sometimes come back as prose instead of a structured card.** The system prompt asks the
  model to prefer structured output for concrete book results, but it doesn't always comply — both forms
  are grounded and correct, the frontend just renders one as cards and the other as text. See
  [ARCHITECTURE.md](ARCHITECTURE.md).
- **A retry pause, or occasionally a full `event: error`, if you run through this script very quickly
  several times in a row.** Groq's free tier is 30 requests/minute — rapid-fire demo re-runs can trip it.
  Space out repeated full run-throughs by a minute or so.
- **`availability: "unknown"`** on a book card is a real status from Open Library's Availability API (not
  every edition is in the Internet Archive lending program), not a broken lookup.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Every reply is the generic "Unable to reach AI service" error | `GROQ_API_KEY` or `PINECONE_API_KEY` missing/invalid | Check `server/.env` against `server/.env.example`; see [README §2](README.md#-local-setup) |
| Server crashes on startup | Set `LOGFIRE_TOKEN` without the matching extra installed | Run `uv sync` in `server/` — `pyproject.toml` pins `logfire[fastapi]` |
| Logfire shows `401 Unauthorized` / `Failed to export span batch` in logs | Used a Logfire read token instead of a write token | Regenerate under **Settings → Write tokens**; see [README's Logfire setup steps](README.md#-local-setup) |
| Policy answers cite the wrong number or say "no information found" | Seed data not upserted yet | Run `pinecone-scripts/upsert_pinecone_records.py` (see [README §2](README.md#-local-setup)) |
| Book question never calls `search_catalog`, or an `event: error` right after a stalling "Let me check..." text | A transient Groq tool-calling quirk, mitigated in code (`ModelRetry` + `run_stream_events()`, see [ARCHITECTURE.md](ARCHITECTURE.md)) | Retry the same question — if it fails consistently across many attempts, check the server logs for the real exception |
