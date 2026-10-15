---
title: Every free tier has a clause
date: 2027-01-05
order: 10
unlisted: true
series: Part 10 of 18
description: People ask if running on $0 a month is a gimmick. It's a constraint, and constraints are where design happens. Every free tier in my stack has a clause meant to make you upgrade.
---
People ask whether running LibSync on $0 a month is a gimmick. I think it's a constraint, and constraints are where the design happens. Every free tier in my stack has a clause meant to make you upgrade, and each clause has to be handled by something other than my attention.

I set one non-negotiable rule: $0. Claude Code turned each clause into a design decision.

## The ledger

| The clause | What LibSync does about it |
|---|---|
| **Render's free web service** sleeps after 15 idle minutes and can take about 50 seconds to wake. | Replies stream over server-sent events, so a patron sees activity immediately instead of a blank spinner. |
| **Pinecone Starter** indexes pause after three weeks idle. | A weekly GitHub Actions keep-alive queries the index. |
| **The free instance has no durable disk.** | The browser keeps the conversation (in IndexedDB) and resends it with every turn. The server holds only a bounded, time-limited in-memory store as a fallback. A cold start doesn't erase a conversation. |
| **The Hugging Face fallback** grants roughly $0.10 a month of credit. | It sits last in the model chain, so almost nothing reaches it. |

Every tier in the roadmap carries a budget ledger like this: the free-tier ceiling, and a risk rating for how likely it is to bite.

An ops team of one can't watch five dashboards. So each limit has to be turned into code, or into a scheduled check that complains when something is wrong.

## Where the builder slipped

The architecture document described Groq's free tier in **requests per day**. The limit that actually bit was **tokens, per model, per minute and per day.** Claude Code had the right instinct (check the provider's limits) and measured in the wrong unit. I didn't catch it either.

It matters because the two units give very different pictures. Counting requests, the free tier looks generous. Counting tokens, a long system prompt eats the allowance fast. Part 15 is the story of that arithmetic.

## The sentence I was proud of

The part of the design I liked best was a `FallbackModel` over two providers, so one provider's outage couldn't become mine. I liked that sentence a lot.

Hold on to it. It doesn't survive Part 14.

## A postscript on the watchdog

The weekly keep-alive deserves a footnote, because it is itself a free-tier system. One Monday in October it failed. The cause wasn't my code. GitHub Actions' status page showed a critical incident with hosted runners, and neither job ever got a machine to run on. A re-run passed.

That's not a story about my code. It's a reminder that the thing watching your free tiers is also a free tier, and that a failed check deserves a look before a fix. The first question is whether the failure is about your system or about the instrument.

> **Architect's note:** a hard constraint is the most powerful design input an architect has. But make the agent show its arithmetic in the provider's own units, because a plausible-looking limit is the easiest thing to get subtly wrong.

Which free-tier limit changed your architecture the most?

*Part 10 of 18. Next: the first time my deployment pipeline ran for real, it took the site down.*
