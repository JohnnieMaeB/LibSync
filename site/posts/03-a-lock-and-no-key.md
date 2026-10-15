---
title: A lock and no key
date: 2026-10-27
order: 3
unlisted: true
series: Part 3 of 18
description: My retrieval endpoint required an embedding vector that nothing in the codebase could produce. It had tests, and it sat there for eight months.
---
I had a lock and no key. My Pinecone endpoint required a precomputed embedding vector, and nothing in my codebase produced one. It had tests.

## How it got there

In October 2025, Google's Jules agent added a function called `queryPinecone(vector, topK)` to my Node backend, with a mock Pinecone client in the tests. I merged it. When I rebuilt the backend in Python in July 2026, the function came along. It sat there for about eight months.

The tests passed the entire time, which is the interesting part. They were testing that the function called a mock correctly. They had no way to learn that the real index couldn't be queried that way.

## The question nobody had asked

The July 2026 audit asked: *what would have to be true for this to work end to end?*

The answer was a mismatch. My index had been created with `create_index_for_model`, which turns on **integrated embedding**. In that mode Pinecone turns your text into a vector for you, on the server, and you query by sending text: `index.search(inputs={"text": ...})`. You never handle a vector at all.

My endpoint was written for a different kind of index than the one I had. It expected a vector the code never created. Against mocks it returned 200 every time. Against the real service it could not have worked once.

## The fix was deleting code

Claude Code's fix removed more than it added. The agent's retrieval tool collapsed to one argument, the question:

```text
search_library_policies(query: str)
  -> index.search(namespace, top_k=3,
                  inputs={"text": query},
                  fields=["chunk_text", "category"])
  -> the matched chunks go back to the model as the tool result
```

No embedding step. No pass-me-a-vector contract that nothing could satisfy. The model asks a question in words, Pinecone finds the closest policy text, and the model reads what came back.

The first grounded answer was "How much are late fees?", and it returned **$0.25 per day, capped at $5.00 per item.** That came from two policy records, `pol3` and `pol11`, with the numbers copied out of the source rather than recalled from memory. It's the first time the assistant answered a policy question from the library's own words.

## The tests had to change too

The old tests proved a mock worked. The new test uses a fake model (PydanticAI's `FunctionModel`) that issues the tool call, then asserts that the final reply contains the text of the tool's return. In other words, it checks that retrieval reached the answer. A status code proves nothing about that.

## The word to remember

One more detail from that week. The seed set of policy records grew from 10 to 34. Loading it into the live index is done by a GitHub Actions workflow with a **manual trigger**.

On a one-person project, "manual" means "whenever I remember." I didn't think much of it at the time. Keep that word in mind. It comes back in Part 14, and it isn't kind to me.

## What I'd flag

This was a case where a passing test stood in for knowing. I merged the code, and the question the audit later asked (can this actually be called?) didn't come up until then. I'd ask it now, and I ask agents to demonstrate that a feature works against the real service before I call it done.

I'm still working out where the line sits between "mock it so tests are fast and cheap" and "test it live so you know it works." I have a rule of thumb (mock in unit tests, run real evals on a schedule), but I'd like to hear how other people draw it.

> **Architect's note:** tests that pass against a mock prove the mock works. For anything an agent builds, ask it to walk the real path end to end, against the real service, before you call it done.

Which "working" endpoint of yours has never actually been called end to end?

*Part 3 of 18. Next: the one thing the model is never allowed to do.*
