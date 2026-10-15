---
title: The scorecard
date: 2027-03-02
order: 18
unlisted: true
series: Part 18 of 18
---
Eighteen posts ago I said this was about trust, one layer at a time. Here's the scorecard after six tiers: Claude Code as builder, me as architect.

What Claude Code was good at: turning each free-tier clause into a design, writing a decision record for every choice, researching with sources, auditing its own work when asked, and, when the evals failed, diagnosing in layers instead of patching the first symptom.

What it got wrong: tests that shared its own assumptions. A demo script claiming the index held 34 records while the live index held 10. An output type that let non-answers through, a pipeline that took production down on its first run, a quota modeled in the wrong unit, and evals that spent production's budget. Even this series: the first draft said 107 tests. It was 136.

What I got wrong: I pasted 2,300 tokens of reference documents into a prompt, merged an endpoint that could never work, and left a manual step with no owner.

What the architect actually did: set the $0 rule, brought the library knowledge and the reason to care, learned library technology hands-on by building against it, asked "is this how libraries really do it?" until the plan changed, chose MIT over the AI's AGPL recommendation, kept the irreversible calls (license, going public, merges) in human hands, and rejected two drafts of this series before it got good.

If I had to give anyone directing an AI coding agent five rules:
1. Separate the author from the checker: evals, a real browser, real data.
2. Make it write things down: plans, definitions of done, decision records, exit conditions.
3. Delegate goals, and demand the numbers.
4. Tell it which budgets belong to production.
5. Question the frame, not just the code.

Where it stands: Tiers 1 to 6 of nine are built, a weekly eval run guards it, and everything is MIT licensed in the open. Next: staff sign-in, a trust-and-compliance phase (AI disclosure, zero data retention, a per-library off switch, a WCAG audit), then document upload and the Koha and Polaris drivers. All at $0 a month, with two flagged exceptions: app-store fees and SAML single sign-on.

The AI conversation keeps splitting into hype and panic. This project is my third option: build small, check everything, keep a human one click away, and ask the people it's for.

I started this series because I was learning in a vacuum. The most useful thing you can do with it is correct me: librarians, accessibility specialists, engineers, anyone who knows where this is naive. And if you run a library that would like to try it, I'd love a pilot. Everything's here: https://github.com/JohnnieMaeB/LibSync

If you work in a library: what would an AI assistant have to prove before you'd put it at your desk?

LibSync build log, Part 18 of 18. Tier 8 updates will follow as they ship.
