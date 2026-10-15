---
title: Two ways a non-answer looked like an answer
date: 2026-11-10
order: 5
unlisted: true
series: Part 5 of 18
description: My agent kept finishing early. Two different bugs, both from one line in the output type, and neither raised an error.
---
My agent kept finishing early. Twice, for different reasons, it mistook text that only looked like an answer for the answer. Both bugs trace back to one line in the design Claude Code and I settled on:

```python
output_type=str | BookResult
```

## What that line says

In PydanticAI, `output_type` tells the agent what counts as a finished answer. Mine says: either plain text (`str`), or a structured `BookResult` when the model has concrete catalog results to show. That lets the interface draw real book cards from data instead of scraping prose.

It's a good design for the happy path. But look at what it also says: **any text the model produces is a valid way to finish.** Because `str` is acceptable, the agent will accept the first string-shaped thing it gets. That's usually fine. Twice it wasn't, and both times I saw it only against a real model, live.

## Bug 1: leaked tool calls

The model sometimes wrote its tool call into the reply instead of issuing one. It looked like this:

```text
<function=search_catalog{...}
<search_catalog>{...}</search_catalog>
{"type": "function", "name": "search_catalog", ...}
```

To the agent, each of those is a perfectly good string, so the run would end and a patron would have seen markup where an answer should be.

**The fix** is an `output_validator`. It matches those patterns and raises `ModelRetry`, which tells the framework to send the model back to try again. `retries=5` gives it room to converge on a real tool call. Note what this is: a check that the answer isn't a *disguised non-answer*, not a check that the answer is correct.

## Bug 2: narration that ended the run

Streaming was first built on `run_stream()`, which commits to the first content that matches the output type. A model that says "I'll check the catalog..." before calling a tool had that sentence accepted as the final answer. The tool call that followed was silently dropped.

**The fix** is `run_stream_events()`, which runs the whole graph to completion so the tool call after the narration still happens. The client also had to learn to replace the cumulative text when a new text part starts, so the opening narration doesn't pile up above the real answer.

## Why these are the expensive kind

Neither bug raised an exception. Neither failed a test. Each produced something shaped like a reply. There was no stack trace to follow and nothing for monitoring to flag, because as far as the system could tell, it had answered.

And neither was visible in the code. Reading `output_type=str | BookResult`, you'd see a reasonable declaration. The problem only appears when you ask what the cheapest thing is that satisfies the type, and then you watch a real model supply it.

A caveat on this post: the model that leaked those formats was `llama-3.3-70b-versatile`, which Groq has since retired (Part 1 has the story). I don't know how often the models I use now would leak a tool call, since I haven't measured. The guard stays regardless, because the failure is a property of how the type is declared, not of one model.

## What I took from it

This is where "the tests pass" stopped being a place I'm willing to stop. A test I write will usually describe the world as I imagine it, and a language model doesn't live in that world. It emits whatever is probable, and sometimes what's probable is a tool call written out as text.

If you build with agents, I think the most useful review habit is reading the type signature before the logic. Ask what the lowest-effort valid output is. Then put the agent in front of real traffic, because it designs for the happy path unless you show it the unhappy one.

> **Architect's note:** review the type signature, not just the logic. Ask "what's the cheapest thing that satisfies this type?" Then feed the agent real traffic, because it designs for the happy path unless you show it the unhappy one.

Where does your agent's output type let a non-answer through?

*Part 5 of 18. Next: the hardest feature to build was a sentence.*
