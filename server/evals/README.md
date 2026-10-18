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
| `MentionsAll` | each required fact appears in the reply (any one of its listed alternatives; text is normalized first: case, curly quotes, non-breaking spaces and hyphens) |
| `MentionsNone` | no forbidden phrase appears: fabricated policies, leaked system-prompt tags |
| `NonEmptyReply`, `NoLeakedToolSyntax` | applied to every case |

A case passes only if all of its checks pass.

## Policy faithfulness (HHEM, reported, not gating)

Every answer that used the policy search also gets a score from Vectara's
[HHEM-2.1-Open](https://huggingface.co/vectara/hallucination_evaluation_model), a small open model that rates how
well the retrieved policy text supports the answer (0 = unsupported, 1 = supported). It catches what the
number check in `app/grounding.py` can't: invented details with no number in them, like "the renewal option will be
removed" for overdue items. See [`faithfulness.py`](faithfulness.py).

- **It doesn't gate the run.** HHEM is about 67% accurate on adversarial benchmarks, so answers scoring below 0.5
  are listed in the summary for a person to read.
- **Answers are cleaned first.** Markdown, emoji, referrals to staff, offers of help and pleasantries are removed
  before scoring. None of those are in the policy text, so HHEM would count them as unsupported: on the real renewal
  policy, a correct answer ending "ask library staff" scored 0.13, and 0.98 without that sentence. An invented
  detail scored 0.01.
- **It only runs where torch is installed.** The weekly workflow installs CPU torch and transformers; locally,
  install them into the server environment to get scores (`--no-hhem` skips it). It never runs in production.

## The dataset

[`dataset.py`](dataset.py) holds 28 cases across policy (each fact traced to a seed record id in
`pinecone-scripts/upsert_pinecone_records.py`), catalog, research, citation, honesty boundaries, persona,
multi-turn continuity, language access (Spanish and Chinese questions), and prompt-injection resistance. Most mirror a turn in [DEMO_SCRIPT.md](../../DEMO_SCRIPT.md).
When you change the seed data or the system prompt, update the affected cases in the same PR.

## In CI

[`agent-evals.yml`](../../.github/workflows/agent-evals.yml) runs the suite weekly and on demand (Actions → Agent
Evals → Run workflow, optionally with a model override). It's kept out of the per-push `ci.yml` because it spends
real free-tier quota and depends on third-party uptime. The offline harness tests in
`tests/test_evals.py` do run on every push.

## Pre-flight: the index must match the seed file

Before spending any LLM tokens, the runner checks that every record in `pinecone-scripts/upsert_pinecone_records.py`
is in the live index with the same text and category (`evals/index_sync.py`). If not, it stops and reports the
missing and stale ids and the fix (run the Pinecone IaC workflow). Skip it with `--skip-index-check`. This exists
because stale data makes a correct, honest answer ("the policy doesn't list a color price") look like an agent failure.
