---
title: The smallest change that makes data per-library
date: 2027-02-23
order: 17
unlisted: true
series: Part 17 of 18
description: To make one assistant serve many libraries, I didn't start with a database. I asked what the smallest change was that makes the data per-library.
---
To make one assistant serve many libraries, I didn't start with a database. I started by asking what the smallest change was that makes the data per-library.

## The requirement

Each library's policies (fines, loan periods, room rules) must answer only that library's patrons. A patron at one library must never get another library's late fee.

Pinecone's documented pattern for multi-tenant retrieval is a **namespace per tenant**: a physically separate partition of the index. It gives real isolation, and deleting a namespace offboards a library completely.

## The obvious design, and the one that shipped

The obvious design is a tenants table that maps each library to its namespace, with a place for configuration. The Tier 8 plan proposed one.

Claude Code skipped it for the groundwork:

- The embeddable widget already sends an `X-LibSync-Library` header. The namespace *is* the library id.
- If a namespace with that name exists in the index, that library gets its own policies. If not, it gets the shared demo set.
- So the moment a library uploads its documents, it switches over automatically. A new library works on day one. There's no configuration to drift out of sync with reality, because the index itself is the record of who exists.

That's "activation by existence rather than config," and it means a feature whose purpose is isolation needed no new service to run.

## Two details that mattered more than the design

**1. The id arrives in a header, so it's untrusted.** It's validated against `^[a-z0-9][a-z0-9-]{0,62}$`. Anything that doesn't match counts as "no library." A test sends `../../ns-other` and asserts it resolves to the shared set. A request header can never be used to select an arbitrary namespace, because a request header is just text somebody typed.

**2. Listing namespaces is a network call to Pinecone.** So the list is cached for five minutes, rather than adding a round trip to every policy search.

## Observability, nearly free

The agent is built with a metadata callable, so every run carries its `library_id` on its Logfire trace. Per-library usage statistics, which a later tier needs for a dashboard, become a query over traces that already exist, not a second logging pipeline to build and keep running.

## Why this is the same story as everything else

It's the same theme, at the data layer. Before a library can trust the assistant, it has to be certain the assistant isn't answering with someone else's rules. The rule from Part 2, grounded or "I don't know," has a corollary: grounded in *whose* documents.

## What isn't done

This is groundwork, not multi-tenancy. Library document upload hasn't shipped, so as far as I know no library has its own namespace yet, and everyone gets the shared set. The isolation machinery exists and is tested, but it hasn't yet carried a real library's data. I don't want to call it finished until it has, and I'd like to hear from anyone who has run a multi-tenant retrieval system about what broke once real tenants arrived.

> **Architect's note:** ask the agent for the smallest change that could work. Left alone, agents reach for new tables and new services, and every one is something a one-person project has to run.

How do you handle tenant isolation in your systems?

*Part 17 of 18. Next: the scorecard.*
