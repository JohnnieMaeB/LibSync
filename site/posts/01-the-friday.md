---
title: The Friday
date: 2026-10-13
order: 1
unlisted: true
series: Part 1 of 18
---
On Friday, October 2: CI green, 136 tests passing. I opened the preview of my own app, asked it for a sci-fi audiobook, and got: "All models from FallbackModel failed (2 sub-exceptions)."

I'd love to say monitoring caught it. The monitoring was me, looking. I screenshotted the error and sent Claude Code one line: "we seem to have a bug in the pr."

The architecture had a primary LLM and a fallback, so one provider's bad day couldn't take the app down. Both failed the same way: 404 model_not_found. Groq had retired llama-3.3-70b-versatile. Novita had retired DeepSeek-V3.2-Exp. Production called the same two models, so it was down too, showing patrons a raw exception string.

Here's the uncomfortable part. Claude Code wrote the app and it wrote the tests, so the tests believed what the code believed: that the models exist. Every test mocks the model. 136 green checks, zero ability to notice.

So I asked for the one thing a test suite from the same author can't be: evals that run the real agent against the real model, tools and data. First run: 0 out of 22. After swapping in models that still existed: 12 out of 22. What remained was more interesting than the outage:

- my vector index held 10 of its 34 policy records
- two-thirds of my system prompt was reference documents written for staff at a desk
- the evals themselves had drained the fallback provider's monthly credit

None of it is exotic. It's what happens when the builder and the checker are the same mind and the architect is stretched thin. Over the next 17 weeks I'll walk through how a green CI got here, one layer of trust at a time, including whose mistake each one was.

Architect's note: an AI that writes both your code and your tests will agree with itself. The checks that matter are the ones that can fail for reasons the builder never imagined.

What's the best thing your green CI ever hid from you?

LibSync build log, Part 1 of 18. Next: the first version of this chatbot, and the sentence it was most confident about.
