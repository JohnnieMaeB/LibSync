# Contributing to LibSync

LibSync is a portfolio project, but it's built and tested like a real one — PRs, issues, and questions are
welcome. This doc covers the mechanics; [README.md](README.md) covers setup and [ARCHITECTURE.md](ARCHITECTURE.md)
covers how the pieces fit together and why.

## Before you start

- Read [README.md § Local Setup](README.md#-local-setup) to get the backend and frontend running.
- Skim [ARCHITECTURE.md](ARCHITECTURE.md) if your change touches the agent, tools, or session handling —
  it explains the reasoning behind choices that aren't obvious from the code alone (e.g. why Groq is
  primary and HF is fallback-only, why the session store is in-process rather than a database).
- Check the [tiered roadmap](README.md#-future-enhancements) if you're planning something bigger than a
  bug fix — it may already be scoped in a later tier, and aligning with that saves rework.

## Project layout

```
server/         Python/FastAPI + PydanticAI backend (uv-managed)
client/src/     Frontend source of truth (vanilla JS/HTML/CSS)
docs/           GitHub Pages copy, generated from client/src/ — never hand-edit
pinecone-scripts/  IaC scripts for the Pinecone policy index
scripts/        Repo-level tooling (currently just sync-docs.js)
```

## Making a backend change

```bash
cd server
uv sync
uv run pytest
```

- Tests use `FunctionModel`/`FallbackModel` overrides to fake LLM behavior and `httpx.MockTransport` to
  fake Open Library — no live API calls, no API keys needed to run the suite.
- If you add a new `@chat_agent.tool` or `@chat_agent.tool_plain`, add a test that asserts the tool is
  actually invoked for a representative prompt (see `tests/test_chat.py` for the pattern: a
  `FunctionModel` that issues a `ToolCallPart` on the first turn and grounds its reply in the
  `ToolReturnPart` on the next). Don't just test the service function in isolation — the point is
  confirming the agent actually reaches for the tool.

## Making a frontend change

```bash
cd client/src
npm install
npm test
```

After editing anything under `client/src/`, resync `docs/` before committing:

```bash
npm run sync-docs
```

CI fails the build if `docs/` doesn't match what `sync-docs` produces, so this isn't optional — it's what
keeps the two from drifting the way they did before Tier 1.

## Commit / PR expectations

- Keep the budget constraint in mind: no change should require a paid tier on Groq, Pinecone, Render,
  Open Library, or Logfire. If a change needs one, flag it explicitly rather than assuming it's fine.
- Run the relevant test suite(s) before opening a PR. CI runs both (`server-tests`, `client-tests`) plus
  the docs-sync check on every PR.
- Prefer a small, focused PR over a large one spanning multiple tiers of the roadmap.
