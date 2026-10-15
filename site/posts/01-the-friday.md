---
title: The Friday
date: 2026-10-13
order: 1
unlisted: true
series: Part 1 of 18
description: CI was green with 136 tests passing, and the app was down. How a preview exposed that the builder and the tests shared the same blind spot.
---
On Friday, October 2, CI was green and 136 tests were passing. I opened the preview of my own app, asked it for a sci-fi audiobook, and got this:

> All models from FallbackModel failed (2 sub-exceptions).

I'd love to say monitoring caught it. The monitoring was me, looking. I screenshotted the error and sent Claude Code one line: "we seem to have a bug in the pr."

## What the error meant

LibSync's agent is built with a primary language model and a fallback, so one provider's bad day can't take the app down. `FallbackModel` tries the first model and, if that fails, moves on to the next. It's a sensible design, and I'd been a little proud of it.

Both providers failed in the same way: `404 model_not_found`. Groq had retired the model I was using, `llama-3.3-70b-versatile`. Novita, the provider behind my fallback, had retired `DeepSeek-V3.2-Exp`. A fallback chain can route around one dead provider. It cannot route around two, because the failure was a shared assumption, not an outage: both fallbacks assumed the model I'd named still existed.

Production called the same two models, so production was down too. And because nothing translated the failure, patrons would have seen that raw exception string.

## Why 136 green tests couldn't see it

This is the part that bothers me most. Claude Code wrote the app, and it wrote the tests. So the tests believed what the code believed: that the models exist. Every one of those tests mocks the model, which means none of them ever calls it.

That isn't a flaw in any individual test. It's a property of the setup. When the same author writes the code and the checks, the checks inherit the author's blind spots. A suite like that can tell you the code is internally consistent. It can't tell you the world still matches what the code assumes.

So I asked for the one thing a test suite from the same author can't be: evals that run the real agent against the real model, real tools and real data. Twenty-two known-answer cases, each with a concrete pass condition.

## What the evals found

The first run scored 0 out of 22. After swapping in models that still existed, it scored 12 out of 22. What remained was more interesting than the outage:

- My vector index held 10 of its 34 policy records, so the assistant had never heard of most of the library's own policies.
- Two-thirds of my system prompt was reference documents written for staff at a desk.
- The evals themselves had drained the fallback provider's monthly credit.

None of that is exotic. It's what happens when the builder and the checker are the same mind and the architect is stretched thin. I'd been splitting my attention between a full-time job, grad school and this, and the one reliable safeguard was whether I happened to open the right page on the right day.

## What I want from this series

Over the next seventeen posts I'll walk through how a green CI got here, one layer of trust at a time: the answers, the interface, the pipeline, and the evals that finally caught this. I'll include whose mistake each one was. Some were Claude Code's. Some were an earlier agent's. Some were mine.

I'm also not sure I've found the best fix. I know evals caught what tests couldn't, but I'm still learning what a good eval suite for an agent looks like, and I expect people who do this for a living will see gaps I don't. If that's you, I'd like to hear them.

> **Architect's note:** an AI that writes both your code and your tests will agree with itself. The checks that matter are the ones that can fail for reasons the builder never imagined.

What's the best thing your green CI ever hid from you?

*Part 1 of 18. Next: the first version of this chatbot, and the sentence it was most confident about.*
