---
title: The smallest change that makes data per-library
date: 2027-02-23
order: 17
unlisted: true
series: Part 17 of 18
---
To make one assistant serve many libraries, I didn't start with a database. I started by asking what the smallest change was that makes the data per-library.

Each library's policies (fines, loan periods, room rules) must answer only that library's patrons. Pinecone's documented pattern for multi-tenant RAG is a namespace per tenant: physical isolation, and deleting the namespace offboards a library completely.

The obvious design is a tenants table mapping each library to a namespace. Claude Code skipped it:
- The widget already sends an X-LibSync-Library header. The namespace is the library id.
- If a namespace with that name exists in the index, that library gets its own policies. If not, it gets the shared demo set.
- So the moment a library uploads its documents, it switches over automatically. A new library works on day one. There's no config to drift out of sync.

Two details mattered more than the design:

1. The id arrives in a header, so it's validated against ^[a-z0-9][a-z0-9-]{0,62}$. Anything else counts as "no library." A test sends "../../ns-other" and asserts it resolves to the shared set. A request header can never select an arbitrary namespace.

2. Listing namespaces is a network call to Pinecone, so the list is cached for five minutes instead of adding a round trip to every policy search.

Observability came almost free: the agent is built with a metadata callable, so every run carries library_id on its Logfire span. Per-library usage stats become a query over traces that already exist.

Same theme as everything else, at the data layer: before a library can trust the assistant, it has to be certain the assistant isn't answering with someone else's rules.

Architect's note: ask the agent for the smallest change that could work. Left alone, agents reach for new tables and new services, and every one is something a one-person project has to run.

How do you handle tenant isolation in your systems?

LibSync build log, Part 17 of 18. Next: the scorecard.
