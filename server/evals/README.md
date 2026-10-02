# Agent evals

Live behavioral checks for the LibSync agent, built on
[pydantic-evals](https://ai.pydantic.dev/evals/). `server/tests/` proves the code works with every model and API
mocked out; these prove the *agent* works — the real model, the real tools, the real seed data.

```bash
cd server
uv run python -m evals.run                                  # full suite (~8 min on Groq's free tier)
uv run python -m evals.run --case late-fees --case renewals # just these cases
uv run python -m evals.run --model groq:qwen/qwen3.8-27b    # vet a different model before swapping it in
uv run python -m evals.run --with-fallback                  # whole FallbackModel chain (spends HF credit)
```

By default the suite runs the **primary Groq model alone**. With the fallback chain enabled, every eval turn that
hits Groq's rate limit spills onto the Hugging Face fallback, and one full run used up its free monthly credit
(about $0.10). Use `--with-fallback` only when you specifically need to test the chain.

Needs `GROQ_API_KEY` and `PINECONE_API_KEY` (from `server/.env` or the environment). Exits non-zero if fewer
than `--threshold` (default 85%) of cases pass, and writes per-case results to `evals/results.json`
(gitignored).

## What a case checks

Every case runs one conversation through `chat_agent` and gets these checks, all deterministic string or
tool-name comparisons (no LLM-as-judge, so a failure always has a concrete reason):

| Evaluator | Passes when |
|---|---|
| `CalledTools` | the expected tool(s) ran on the final turn, and no forbidden ones did |
| `MentionsAll` | each required fact appears in the reply (any one of its listed alternatives, case-insensitive) |
| `MentionsNone` | no forbidden phrase appears: fabricated policies, leaked system-prompt tags |
| `NonEmptyReply`, `NoLeakedToolSyntax` | applied to every case |

A case passes only if all of its checks pass.

## The dataset

[`dataset.py`](dataset.py) holds 22 cases across policy (each fact traced to a seed record id in
`pinecone-scripts/upsert_pinecone_records.py`), catalog, research, citation, honesty boundaries, persona,
multi-turn continuity, and prompt-injection resistance. Most mirror a turn in [DEMO_SCRIPT.md](../../DEMO_SCRIPT.md).
When you change the seed data or the system prompt, update the affected cases in the same PR.

## In CI

[`agent-evals.yml`](../../.github/workflows/agent-evals.yml) runs the suite weekly and on demand (Actions → Agent
Evals → Run workflow, optionally with a model override). It's kept out of the per-push `ci.yml` because it spends
real free-tier quota and depends on third-party uptime. The offline harness tests in
`tests/test_evals.py` do run on every push.
