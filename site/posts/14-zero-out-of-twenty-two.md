---
title: 0/22
date: 2027-02-02
order: 14
unlisted: true
series: Part 14 of 18
description: My first eval run scored 0 out of 22. Every case failed on the same line, which hid the interesting failures behind it. Unwinding it took three layers.
---
My first eval run scored 0 out of 22. Every case failed on the same line, which meant the interesting failures were hiding behind it. Unwinding it took three layers.

## Why evals at all

After the Friday in Part 1, I asked Claude Code for the one thing my 136 tests couldn't be: a check from a different instrument. Same author, different tool.

The result is a suite of 22 known-answer cases, built with `pydantic-evals`, that run the real agent against the real model, tools and seed data. Each case checks behavior with plain code, not another AI acting as judge. It asks: did the agent call the right tool? Does the reply contain the specific fact from the policy record, such as "$5" in a late-fee answer? Did it admit a gap instead of inventing a policy? Every failure has a concrete reason you can reproduce.

## Layer 1: the models

Claude Code called each provider directly instead of going through `FallbackModel`, so it could see each error on its own. Groq returned `404 model_not_found` for `llama-3.3-70b-versatile`. Novita returned `404 MODEL_NOT_FOUND` for `DeepSeek-V3.2-Exp`. Both were retired.

It listed which models each account still offered, swapped in `gpt-oss-120b` and `DeepSeek-V4-Flash`, and re-ran: **12 out of 22**.

## Layer 2: the facts

The remaining failures were policy questions where the agent called `search_library_policies` correctly and still left out the number. Because the checks look for the specific fact and not just the tool call, each failure had a clear reason: the facts weren't coming back.

Claude Code looked at the index itself. `describe_index_stats()` reported `total_vector_count: 10`.

The seed script defines 34 records. It had grown from 10 to 34 on July 11. Loading it into the index is a manually triggered workflow, the word I told you to remember in Part 3. Nobody had run it.

For twelve weeks, the live assistant had never heard of the $5 fine cap, renewal limits, holds, hotspots or replacement cards. It answered from the ten records it did have, politely, so nothing looked broken. And the demo script Claude Code wrote the same day says retrieval "covers the full seed set (34 records across 8 categories)." Nothing checked that claim.

After an idempotent upsert, with no code change at all: **17 out of 22**.

## Layer 3: the remaining five

Three were policy replies still missing details, which is a prompt problem and the subject of the next post. Two were `FallbackExceptionGroup` errors again: the fallback provider was returning 402 because its monthly credit was gone.

That one was Claude Code's own mistake. Its first eval runs went through the production fallback chain, so every rate-limited request spilled onto the paid-credit fallback.

## What it adds up to

Three problems in three layers (provider, data, prompt), all invisible to 136 green tests. I'd been proud of "two providers behind a `FallbackModel`." It protects against one provider's bad day. It doesn't protect against a shared assumption: that the models I named still exist.

## Evals need tests too

My on-call rotation is a Monday cron job running the same 22 evals, so the next retired model tells me before it tells patrons.

Its first scheduled run, on October 5, scored **16 out of 22 (73%)** and went red. Mostly the model was right, and my checks were wrong:

- My phrase checks compared straight apostrophes to the curly ones the model writes, and a plain space to the narrow no-break space it puts between a number and a unit. Four correct answers scored as failures.
- My "idempotent" upsert only ever inserted *missing* records, so two records I'd edited in the seed file never reached the index.
- One failure was real: asked whether a book was on Libby, the assistant answered with book cards instead of saying it can't check.

After the fixes and an index sync, CI scored **20 out of 22 (91%)**. The two remaining misses turned out to be checks that were too narrow, which I've since broadened. The lesson is a little embarrassing: the test of the test is a real run, and so is the test of the data underneath it.

I should be clear about what this does and doesn't show. Twenty-two cases is a small suite, and I wrote the checks, so they encode what I thought to check. I don't know what an eval suite for a library assistant should contain that I haven't thought of. That's a question I'd like help with.

> **Architect's note:** ask the agent for checks that can fail for reasons it didn't imagine, and tell it which budgets belong to production. An agent has no instinct for what's shared.

Which of your dependencies is a "two providers" illusion?

*Part 14 of 18. Next: the system prompt, and the arithmetic nobody had done.*
