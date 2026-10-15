---
title: Every free tier has a clause
date: 2027-01-05
order: 10
unlisted: true
series: Part 10 of 18
---
People ask if running on $0 a month is a gimmick. It's a constraint, and constraints are where the design happens. Every free tier in my stack has a clause meant to make you upgrade.

I set one non-negotiable rule: $0. Claude Code turned each clause into a design decision:

- Render's free web service sleeps after 15 idle minutes and takes up to about 50 seconds to wake. → Replies stream over SSE, so a patron sees activity immediately instead of a blank spinner.
- Pinecone Starter indexes pause after three weeks idle. → A weekly GitHub Actions keep-alive queries the index.
- The free instance has no durable disk. → History lives in the browser (IndexedDB) and is resent with every turn; the server keeps only a bounded, TTL-evicted in-memory store as a fallback. A cold start doesn't erase a conversation.
- The Hugging Face fallback grants roughly $0.10 a month of credit. → It sits last in the chain.

With an ops team of one, every limit has to be handled by code instead of attention. Every tier in the roadmap carries a budget ledger: the free-tier ceiling, and a risk rating for when it bites.

Here's where the builder slipped. The architecture doc described Groq's free tier in requests per day. The limit that actually bit was tokens, per model, per minute and per day. It had the right instinct (check the provider's limits) and measured in the wrong unit. I didn't catch it either.

And the part I was proudest of: a FallbackModel over two providers, so one provider's outage couldn't become mine. I liked that sentence a lot. Hold on to it.

Architect's note: a hard constraint is the most powerful design input an architect has. But make the agent show its arithmetic in the provider's own units, because a plausible-looking limit is the easiest thing to get subtly wrong.

Which free-tier limit changed your architecture the most?

LibSync build log, Part 10 of 18. Next: the first time my deployment pipeline ran for real, it took the site down.
