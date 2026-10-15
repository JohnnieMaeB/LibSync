---
title: Who's building this, why, and why I'm posting it
date: 2026-10-06
order: 0
unlisted: true
series: Prologue
description: A library AI assistant built on a $0 budget, with Claude Code as the builder and me as the architect, and why I'm writing it all down in public.
---
In 2024 I left a corporate engineering job to find my place in AI. I went to grad school. I worked a public library's patron desk and a university accessibility office. Then I went back to building AI professionally. LibSync is where all of it meets.

This is the first post in a series about building it, and before the technical posts begin I owe you the reasons: what the project is, who it's for, who is actually writing the code, and why I'm talking about any of it in public.

## What I believe

The AI conversation keeps sorting itself into two camps, hype and panic. I'm not in either one. I think we can make AI ethical, interesting and useful, and I care most about the people technology tends to underserve, like disabled people.

I also believe information should be available to everyone and, more importantly, *accessible* to everyone. Those are different things. A library can hold the answer to your question and still make it hard to get, and sometimes the barrier isn't a missing book. It's the social cost of asking a stranger.

I'm autistic, and I'm painfully aware of how design choices can lock someone out of a space. For people like me, walking up to a desk and asking for help can be the barrier. I want an AI that makes asking a library a question easier, with a human always one click away. It isn't meant to replace the librarian. It's meant to make the first question cheaper to ask.

## What LibSync is

LibSync is an AI assistant for public libraries. It answers the things people ask at a library desk: how much is the late fee, can I renew this twice, how do I cite that paper. It answers from sources it can point to, such as the library's own policies and open catalog and research data. When it can't check something, it says so instead of guessing.

That last part matters more than it sounds, and it's a recurring character in this series. A confident wrong answer and a correct one look identical in a demo, and a library patron is the wrong person to hand a confident guess.

I spent most of 2025 operating a Sierra ILS (an integrated library system) behind a public library desk. Building LibSync is how I'm exploring the rest of library technology hands-on: the standards, the vendors and the way real libraries run their systems.

## Who is writing the code

I'm the architect. Claude Code is the builder, and it wrote nearly all of the code you'll read about. The first version, from last October, was mine, with another AI agent's help. Nearly everything built since July is Claude Code working under my direction.

By day I build production AI agents. LibSync is where I explore the same ideas on my own time, in a field I care about. It's a portfolio project on a $0 budget, built around a full-time job and grad school, with no ops team and no QA department. That's exactly how things fall through the cracks, and I'll show you where they did.

So the series has three threads, and every post pulls on all of them:

1. **What Claude Code built**, and how.
2. **What it got wrong**, and what finally caught it. Some of those mistakes were mine, and some belong to an earlier agent. I'll say whose, because naming it plainly is what makes any of this worth reading.
3. **What I did as the architect.** I set constraints, supplied the domain knowledge, asked the questions the agent couldn't, verified, and decided.

Each post ends with an "architect's note": one sentence of advice for anyone directing an AI coding agent. I'm offering it as advice, not as a claim that I always follow it.

## Why I'm talking about any of this

Here's the honest reason: I have a lot left to learn, and I've been trying to learn it in a vacuum. Library technology, agentic coding, accessibility done properly. All three have people who know far more than I do, and a vacuum has nobody to tell you you're wrong.

So I'm doing it in public: what I build, what breaks, and what I get wrong. I'd rather be corrected by someone who knows than be quietly wrong where only I can see it.

Yes, Claude Code helps draft these posts too, and I edit them. The first draft of this very series said we had 107 tests. We had 136. It also claimed that a server restart erased conversations, which stopped being true several versions earlier. Both errors were caught before publishing, and they tell you roughly how the whole series goes.

## What's coming

Eighteen posts. They open with the Friday everything broke, then move through the answers the assistant gives, the interface it gives them in, the pipeline that ships it, the evals that tested it, and finally the question that reshaped the plan: how do real libraries actually run their systems?

Everything is MIT licensed and in the open, including the decision records.

If you work in libraries, accessibility or AI, I have a question for you before we start: **what should I be learning that I don't know to look for?**

*Prologue. Next: Part 1, the Friday the preview died.*
