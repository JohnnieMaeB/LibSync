# What our first agent evals caught in one day

*LibSync engineering notes, October 2026*

LibSync is a $0/month library-assistant agent: PydanticAI on Groq's free tier, with Pinecone for policy
retrieval and Open Library, OpenAlex and Crossref as its tools. By Tier 6 it had 100+ unit tests, and every
one of them passed. Unit tests mock every model and API, though. They show the code is correct, not that
the agent is.

So we wrote 22 known-answer cases with [pydantic-evals](https://ai.pydantic.dev/evals/) and ran them
against the real stack: the real model, real tools and real seed data. Each case checks behavior
deterministically. Did the agent call the right tool? Does the answer contain the actual fact from the
policy record (e.g. "$0.25 per day", "capped at $5")? Did it admit a gap instead of inventing a policy? No
LLM-as-judge, so every failure has a concrete, reproducible reason.

The first day of running them turned up five separate problems, and none of them was visible to the unit
tests.

## 1. 0/22: both models had been retired

The very first run failed every case at the provider. Groq had retired `llama-3.3-70b-versatile`, and
novita had retired the fallback, `DeepSeek-V3.2-Exp`. Both returned `404 model_not_found`. `FallbackModel`
can route around one dead provider, but not two, so **every chat turn in production was failing**. To make
it worse, patrons saw the raw exception text: *"All models from FallbackModel failed (2 sub-exceptions)"*.

**Fix:** current models, vetted by running the eval suite against each candidate before swapping it in. A
failed turn now shows patrons a plain "unable to reach the AI service" message; the real error goes to the
server log.

**Lesson:** a provider can retire a model without warning. A scheduled run against the real model is the
only test that notices.

## 2. 12/22: the index held 10 of its 34 records

With working models, policy questions still failed in a strange way: the agent called the right tool,
then answered without the fact. A direct Pinecone query explained it. Only records `pol1`–`pol10` ever
came back. The index held **10 vectors; the seed script defines 34.** The upload workflow only runs when
triggered by hand, and nobody ran it after the policy set was expanded from 10 to 34. So ever since Tier 1, the
live assistant hadn't known about fine caps, renewal limits, holds, hotspots or replacement cards. It
answered from what it was given, and politely left those out.

**Fix:** re-ran the (idempotent) upload. The suite went from 12/22 to 17/22 with no code change.

**Lesson:** "the tool was called" is a weak check. Checking for the *specific fact* in the reply is what
caught a half-empty index.

## 3. The prompt was mostly reference documents

Groq's free tier caps `gpt-oss-120b` at **8,000 tokens per minute and 200,000 per day**. One request was
about 3,800 tokens, which meant about two requests a minute and about 50 a day. Measuring the system prompt
showed where they went: 64% of it was the RUSA reference guidelines, the ALA Library Bill of Rights and the
ALA Core Values, pasted in word for word. Most of that text is written for desk staff ("is easily
identifiable as a staff member", "shares the search screen") and is useless to a chatbot.

**Fix:** a distilled set of service principles the model can actually act on (clarify ambiguous questions,
no judgment, intellectual freedom, privacy, refer to staff when out of scope), with the sources cited. The
same pass fixed persona lines that invited made-up answers: "aware of *all* library workshops" became "only
ones the policy search returns". Requests dropped to about 2,200 tokens, so about 40% more requests fit in the daily budget.

## 4. The evals used up the fallback's credit

This one was our own fault. The suite first ran through the production `FallbackModel`, so every time Groq
rate-limited an eval turn, the request quietly spilled onto the Hugging Face fallback. Its free credit is
about $0.10 a month. One full suite run used it all up, leaving production with no working fallback.

**Fixes:**
- Evals now target the primary model alone by default (`--with-fallback` to opt in).
- Production now chains **three Groq models**: `gpt-oss-120b`, then `qwen3.8-27b` (19/22 on the suite),
  then `gpt-oss-20b` (18/22). Groq limits each model separately, so that's three daily quotas before the
  paid-credit fallback. We verified the switch live by putting a model that 404s first in the chain.
- The weekly run moved to a low-traffic hour, since it shares the production model's daily budget.

## 5. A CI run that said nothing for 30 minutes

The first scheduled run hit the 30-minute job limit with an empty log. Python buffers output when it isn't
writing to a terminal, and the progress bar doesn't render in Actions. Once we could see output, the cause
was obvious. Groq's daily-limit errors say *"try again in 7m30s"*, and the retry code read that as 30
seconds. It retried every case three times into a wall.

**Fixes:** unbuffered, line-per-case logging; Groq's minute- and hour-scale wait times parsed correctly;
waits too long to be the per-minute limit fail the case immediately; and a 3-minute limit per case.

## 6. The first scheduled run went red, and mostly the model was right

The Monday run scored 16/22 (73%), under the 85% gate. The harness worked; what failed was more instructive:

- **Four "failures" were my checker.** gpt-oss writes a narrow no-break space (U+202F) between a number and its unit
  ("7 days") and curly apostrophes ("doesn’t"). The phrase checks compared plain ASCII, so correct replies, including
  an honest "I'm not seeing piano-lesson programming listed," were scored as misses. Checks now normalize first (NFKC,
  curly quotes and non-breaking hyphens to ASCII, collapsed whitespace), with tests for each.
- **One was stale data.** The live record for `pol7` still said only "$0.10 per page." The seed file added the color
  price on July 11, but the upsert script only inserted ids missing from the index, so edits to existing records never
  arrived (`pol9` too). The model was being honest. The script now updates changed records, and the runner has a
  deterministic pre-flight that compares the live index to the seed file before any LLM call.
- **One was real.** On the Libby question the model called `search_catalog` and returned book cards instead of saying
  it can't check Libby. The prompt now routes those questions to a plain-text answer.

**Lesson:** evals have bugs, and so does the data they check. A red run is a prompt to look at all three: the agent,
the checks, and the data.

## Takeaways

- **Mocked tests and live evals answer different questions.** Both are needed. The unit suite stayed green
  through every problem above.
- **Check facts, not just tool calls.** The most valuable check was "does the reply contain the number from
  record `pol11`?"
- **On a free tier, quotas are a design input.** Prompt size, fallback order and eval scheduling all came
  down to Groq's per-model daily limits.
- **Evals have bugs too.** Compare meaning, not bytes, and verify the data underneath them.
- **Evals cost money too.** A test suite that shares production's budget can take production down, so
  isolate what it touches.

The suite lives in [`server/evals/`](../../server/evals/README.md) and runs weekly in
[Agent Evals](../../.github/workflows/agent-evals.yml).
