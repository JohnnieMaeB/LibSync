---
title: 0/22
date: 2027-02-02
order: 14
unlisted: true
series: Part 14 of 18
---
My first eval run scored 0 out of 22. Every case failed on the same line, which meant the interesting failures were hiding behind it. Unwinding it took three layers.

After the Friday in Part 1, I asked Claude Code for the one thing my 136 tests couldn't be: a check from a different instrument. Same author, different tool.

Layer 1: the models. It called each provider directly instead of through FallbackModel. Groq: 404 model_not_found for llama-3.3-70b-versatile. Novita: 404 MODEL_NOT_FOUND for DeepSeek-V3.2-Exp. Both retired. It listed what each account offered, swapped in gpt-oss-120b and DeepSeek-V4-Flash, and re-ran: 12 out of 22.

Layer 2: the facts. The failures were policy questions where the agent called search_library_policies correctly and still left out the number. The checks look for the specific fact (is "$5" in the late-fee reply?), not just the tool call, so each failure had a clear reason: the facts weren't coming back. describe_index_stats(): total_vector_count: 10.

The seed script defines 34 records. It grew from 10 to 34 on July 11. Loading it is a manually triggered workflow, the word I told you to remember in Part 3. Nobody ran it. For twelve weeks the live assistant had never heard of the $5 fine cap, renewal limits, holds, hotspots or replacement cards, and it answered from what it did have, politely. The demo script Claude Code wrote that same day says retrieval "covers the full seed set (34 records across 8 categories)." Nothing checked. After the idempotent upsert: 17 out of 22, no code change.

Layer 3: the remaining five. Three were policy replies still missing details (the prompt, next part). Two were FallbackExceptionGroup again: the fallback provider was returning 402, monthly credit gone. That one was Claude Code's own mistake. Its first eval runs went through the production fallback chain, so every rate-limited request spilled onto it.

Three problems, three layers (provider, data, prompt), all invisible to 136 green tests. I'd been proud of "two providers behind a FallbackModel." It protects against one provider's bad day, not against a shared assumption: that the models I named still exist.

My on-call rotation is a Monday cron job running the same 22 evals, so the next retired model tells me before it tells patrons. Its first run went red, and mostly the model was right: my phrase checks compared straight apostrophes to the curly ones it writes and a plain space to its narrow non-breaking one, and my "idempotent" upsert only ever inserted missing records, so two edited ones were stale. Evals need tests too, and so does the data they check.

Architect's note: ask the agent for checks that can fail for reasons it didn't imagine, and tell it which budgets belong to production. An agent has no instinct for what's shared.

Which of your dependencies is a "two providers" illusion?

LibSync build log, Part 14 of 18. Next: the system prompt, and the arithmetic nobody had done.
