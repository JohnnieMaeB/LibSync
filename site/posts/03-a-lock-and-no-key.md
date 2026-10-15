---
title: A lock and no key
date: 2026-10-27
order: 3
unlisted: true
series: Part 3 of 18
---
I had a lock and no key. My Pinecone endpoint required a precomputed embedding vector, and nothing in my codebase produced one. It had tests.

In October 2025, Google's Jules agent added queryPinecone(vector, topK) to my Node backend, with a mock Pinecone client in the tests. I merged it. The July 2026 rebuild ported it to Python. It sat there for about eight months.

The audit finally asked the question nobody had: what would have to be true for this to work end to end? The index had been created with create_index_for_model, which turns on integrated embedding. Pinecone embeds your text server-side, and you query with index.search(inputs={"text": ...}), never a vector. The endpoint was written for an index I didn't have, and it returned 200 against mocks the whole time.

Claude Code's fix deleted code. The agent's tool collapsed to one argument:

search_library_policies(query: str) → index.search(namespace, top_k=3, inputs={"text": query}, fields=["chunk_text", "category"]) → the matched chunks go back to the model as the tool result.

First grounded answer: "How much are late fees?" came back as $0.25 per day, capped at $5.00 per item. Two records (pol3 and pol11), with the numbers copied from the source rather than remembered. The tests changed too: a FunctionModel issues the tool call and asserts the reply contains the text of the ToolReturnPart. A status code proves nothing about retrieval.

One more detail from that week. The seed set grew from 10 records to 34, and loading it into the index is a GitHub Actions workflow with a manual trigger. On a one-person project, "manual" means "whenever I remember." Remember that word.

Architect's note: tests that pass against a mock prove the mock works. For anything an agent builds, ask it to walk the real path end to end, against the real service, before you call it done.

Which "working" endpoint of yours has never actually been called end to end?

LibSync build log, Part 3 of 18. Next: the one thing the model is never allowed to do.
