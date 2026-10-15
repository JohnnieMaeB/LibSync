---
title: The scorecard
date: 2027-03-02
order: 18
unlisted: true
series: Part 18 of 18
description: Eighteen posts ago I said this was about trust, one layer at a time. Here's the scorecard after six tiers, with Claude Code as builder and me as architect.
---
Eighteen posts ago I said this was about trust, one layer at a time. Here's the scorecard after six tiers: Claude Code as builder, me as architect.

## What Claude Code was good at

Turning each free-tier clause into a design. Writing a decision record for every choice. Researching with sources. Auditing its own work when asked. And, when the evals failed, diagnosing failures in layers instead of patching the first symptom.

## What it got wrong

- Tests that shared its own assumptions (Part 1).
- A demo script claiming the index held 34 records while the live index held 10 (Part 14).
- An output type that let non-answers through (Part 5).
- A pipeline that took production down on its first run (Part 11).
- A quota modeled in the wrong unit (Part 10).
- Evals that spent production's budget (Parts 14 and 15).
- Even this series: the first draft said 107 tests. It was 136.

## What I got wrong

I pasted 2,300 tokens of reference documents into a prompt (Part 2). I merged an endpoint that could never work (Part 3). I left a manual step with no owner (Part 14). My first UI shipped with no visible keyboard focus (Part 9).

Some of the other mistakes belong to an earlier agent, Google's Jules. They were merged by me, so they're partly mine too.

## What the architect actually did

I set the $0 rule. I brought the library knowledge and the reason to care. I learned library technology hands-on by building against it. I asked "is this how libraries really do it?" until the plan changed (Part 16). I chose MIT over the AI's AGPL recommendation. I kept the irreversible calls (the license, going public) in human hands, and gave merge permission narrowly. And I rejected two drafts of this series before it got good.

Day to day it's steering more than prompting: I give a goal in plain language, Claude Code builds, I check the result in the browser, and when something looks wrong I send a screenshot and one sentence.

## Five rules for directing an AI coding agent

If I had to give anyone five rules:

1. **Separate the author from the checker.** Evals, a real browser, real data.
2. **Make it write things down.** Plans, definitions of done, decision records, exit conditions.
3. **Delegate goals, and demand the numbers.**
4. **Tell it which budgets belong to production.**
5. **Question the frame, not just the code.**

I'm offering these as advice, not as proof that I follow them. I broke most of them on the way to learning them.

## Where it stands

Tiers 1 to 6 of nine are built, a weekly eval run guards the agent, and everything is MIT licensed in the open. What's next:

- Staff sign-in.
- A trust-and-compliance phase: AI disclosure, zero data retention, a per-library off switch, and a WCAG audit.
- Then document upload, and the Koha and Polaris drivers.

All at $0 a month, bar app-store fees and SAML single sign-on.

## The third option

The AI conversation keeps splitting into hype and panic. This project is my third option: build small, check everything, keep a human one click away, and ask the people it's for.

## The ask

I started this series because I was learning in a vacuum. The most useful thing you can do with it is correct me: librarians, accessibility specialists, engineers, anyone who knows where this is naive.

And if you run a library that would like to try it, I'd love a pilot. Everything's here: [github.com/JohnnieMaeB/LibSync](https://github.com/JohnnieMaeB/LibSync).

If you work in a library: what would an AI assistant have to prove before you'd put it at your desk?

*Part 18 of 18. Tier 8 updates will follow as they ship.*
