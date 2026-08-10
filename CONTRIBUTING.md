# Contributing to LibSync

LibSync is a portfolio project, but it's built and tested like a real one — PRs, issues, and questions are
welcome. This doc covers the mechanics; [README.md](README.md) covers setup and [ARCHITECTURE.md](ARCHITECTURE.md)
covers how the pieces fit together and why.

## Before you start

- Read [README.md § Local Setup](README.md#-local-setup) to get the backend and frontend running.
- Skim [ARCHITECTURE.md](ARCHITECTURE.md) if your change touches the agent, tools, or session handling —
  it explains the reasoning behind choices that aren't obvious from the code alone (e.g. why Groq is
  primary and HF is fallback-only, why the session store is in-process rather than a database). For the
  mechanical "what calls what, in what order" version, see [server/TRACE.md](server/TRACE.md).
- Check the [tiered roadmap](README.md#-future-enhancements) if you're planning something bigger than a
  bug fix — it may already be scoped in a later tier, and aligning with that saves rework.

## Project layout

```
server/         Python/FastAPI + PydanticAI backend (uv-managed)
  app/routers/     /agent (AG-UI, primary), /chat + /chat/stream (fallback), /citation, /api/query
  app/services/    Pinecone, Open Library, OpenAlex, Crossref, citeproc-py clients
app/             Frontend source of truth (React + TypeScript, Vite)
pinecone-scripts/  IaC scripts for the Pinecone policy index
scripts/        build-site.js — runs `vite build` on app/ into a build dir, with an optional
                VITE_API_BASE_URL override, used by the prod-publish and PR-preview workflows (see below)
```

GitHub Pages content itself lives on the `gh-pages` branch (production at its root, PR previews under
`pr-preview/pr-<number>/`), published by CI rather than hand-committed — see
[README § PR Previews and Deployment](README.md#-pr-previews-and-deployment).

## Making a backend change

```bash
cd server
uv sync
uv run pytest
```

- Tests use `FunctionModel`/`FallbackModel` overrides to fake LLM behavior and `httpx.MockTransport` to
  fake Open Library/OpenAlex/Crossref — no live API calls, no API keys needed to run the suite.
- If you add a new `@chat_agent.tool` or `@chat_agent.tool_plain`, add a test that asserts the tool is
  actually invoked for a representative prompt (see `tests/test_chat.py` for the pattern: a
  `FunctionModel` that issues a `ToolCallPart` on the first turn and grounds its reply in the
  `ToolReturnPart` on the next). Don't just test the service function in isolation — the point is
  confirming the agent actually reaches for the tool. `tests/test_agent_endpoint.py` has the equivalent
  pattern for the AG-UI transport (`/agent`), asserting on the actual SSE event sequence, including that a
  tool emitting a card shows up as a `CUSTOM` event.
- If your tool should render as a card on the AG-UI transport, return a
  `pydantic_ai.messages.ToolReturn(return_value=..., metadata=_custom_event("your_event_name", payload))`
  instead of a plain string — see `search_catalog`/`search_scholarly_works`/`lookup_and_cite` in
  `app/agent.py` for the pattern, and `_custom_event()` itself for why this works (it rides on the same
  tool-return mechanism `AGUIEventStream` already inspects — no new plumbing needed).
- New third-party API client? Follow the existing service pattern: a plain async function taking a shared
  `httpx.AsyncClient`, an in-process TTL cache (see `open_library_service.py`/`openalex_service.py` for the
  pattern), and identify the app to the API's polite pool (`User-Agent` header or a `mailto=`/contact-email
  param) rather than going fully anonymous.

## Making a frontend change

```bash
cd app
npm install
npm test
```

Nothing to sync manually — merging to `main` builds `app/` and publishes it automatically
([`deploy-pages.yml`](.github/workflows/deploy-pages.yml)), and every PR gets its own live preview at
`pr-preview/pr-<number>/` ([`pr-preview.yml`](.github/workflows/pr-preview.yml); see
[README § PR Previews and Deployment](README.md#-pr-previews-and-deployment) for how it's wired up).
CI still runs a `vite build` of `app/` on every push/PR as a sanity check ([`ci.yml`](.github/workflows/ci.yml)),
independent of the deploy workflows' own build.

The AG-UI transport lives in [`app/src/hooks/useAgentStream.ts`](app/src/hooks/useAgentStream.ts), built on
`@ag-ui/client`'s `HttpAgent` talking to `POST /agent` (the older `/chat`/`/chat/stream` fallback transport
isn't called by the current frontend). If you're adding a new card type, extend the `onEvent` switch's
`CUSTOM` case in that hook and add a matching component under
[`app/src/components/`](app/src/components/) — cards and streaming text are tracked as an ordered `blocks`
array per bot message (see `BotEntry` in [`app/src/types.ts`](app/src/types.ts)) specifically because text
and cards can arrive in either order and must not clobber each other (see ARCHITECTURE.md's "Frontend text
and cards must coexist" entry for why that's a real, previously-shipped bug, not a hypothetical).

**Never use `dangerouslySetInnerHTML` (or any raw-HTML DOM API) on model output or other untrusted text.**
Model output is untrusted — it can echo retrieved text or be steered via prompt injection. Any new bot-facing
text must go through `renderInlineMarkdownNodes()` / `SafeMarkdown` in
[`app/src/lib/markdown.tsx`](app/src/lib/markdown.tsx), which builds real React elements (`<strong>`, `<em>`,
an `<a>` restricted to `http(s)` hrefs) and emits everything else as plain text nodes — never raw markup. If
you need a new inline format, extend `INLINE_MARKDOWN_PATTERN` and its handler there rather than reaching for
`dangerouslySetInnerHTML`. [`app/src/lib/markdown.test.tsx`](app/src/lib/markdown.test.tsx) has a regression
test asserting `<script>`/`<img onerror>` in model output never becomes live markup — add a case there if you
touch this path.

## Commit / PR expectations

- Keep the budget constraint in mind: no change should require a paid tier on Groq, Pinecone, Render, Open
  Library, OpenAlex, Crossref, or Logfire. If a change needs one, flag it explicitly rather than assuming
  it's fine.
- Don't bump `fastapi` past `<0.137` without checking the pin's comment in `server/pyproject.toml` first —
  it's there to avoid a real CORS-preflight-breaking bug (`opentelemetry-instrumentation-fastapi` 0.63b1
  can't handle FastAPI 0.137+'s `_IncludedRouter`), not an arbitrary version freeze. See
  [ARCHITECTURE.md](ARCHITECTURE.md) for the full explanation.
- Run the relevant test suite(s) before opening a PR. CI runs both (`server-tests`, `client-tests`) on every
  PR, and a preview deploy kicks off separately — see
  [README § PR Previews and Deployment](README.md#-pr-previews-and-deployment).
- Prefer a small, focused PR over a large one spanning multiple tiers of the roadmap.
