---
title: The day the cards disappeared
date: 2026-12-01
order: 7
unlisted: true
series: Part 7 of 18
description: Three bugs only a real browser, a real conversation and a real model provider could produce, and why the unit tests never saw them.
---
The book card appeared for a split second, then vanished. Every unit test was green. They'd been written against an event order that happened not to trigger the bug.

## How cards get to the screen

LibSync streams its replies to the browser over **AG-UI**, an open protocol for sending events from an agent backend to a frontend: message text, tool calls, tool results, and custom events for anything structured, like a book card.

Claude Code and I chose it over the other contender, MCP Apps. The tier plan lays out why. MCP Apps exists so a generic AI client can safely render a *stranger's* tool interface inside a sandbox. My frontend is first-party and already trusts my backend, so that's a problem I don't have. AG-UI also has first-party PydanticAI support, which meant one new dependency and no new architecture.

The migration was also deliberately additive: the old `/chat` endpoint stayed untouched and the new transport went beside it at `/agent`, so a bug in the new path couldn't take down the old one.

A tool becomes a card by returning a `ToolReturn` whose metadata carries a custom event. The catalog search emits one `book_card` event per result, live, as it finds them.

## Three bugs

What follows is three bugs that only a real browser, a real conversation and a real provider could produce.

### 1. Vanishing cards

The real event order for a grounded answer is:

1. `TOOL_CALL_RESULT`
2. `CUSTOM` (the card)
3. `TEXT_MESSAGE_CONTENT` (the model's narration)

The narration comes *after* the card. The frontend handler cleared the message bubble on every text event, so when the narration arrived it wiped the card that had just rendered. The unit tests used event orders in which that never happened.

**The fix:** clear the "Thinking…" placeholder exactly once, on whichever event arrives first, text or card. After that, everything appends. It lives in a function called `ensureContentStarted()`.

### 2. Amnesia from turn two

`AGUIAdapter` folds the user's new message into the conversation history *before* the run starts. So when the run finishes, `result.new_messages()` doesn't contain that message. It only covers what the run generated beyond the history it was given.

The code persisted only `new_messages()`, which silently dropped every user turn. The assistant would answer the first question fine, then forget that you'd ever asked it anything.

**The fix:** store the existing history, plus the request's messages, plus `new_messages()`.

### 3. Raw provider errors

Groq's `tool_use_failed` error, where the API itself rejects a tool call the model generated, escaped `FallbackModel`. The reason is subtle: `FallbackModel` guards the *start* of a stream, not the iteration of a stream it has already handed back. So the retries I'd configured, and the fallback to another provider, never engaged. About two in three attempts at "Find me a sci-fi audiobook" failed, and the patron saw the provider's raw text. (Yes, that's Part 1's prompt.)

**The fix:** buffer events until the first one that isn't `RUN_STARTED`. If what arrives next is a `RUN_ERROR` before any real content, throw the buffer away and retry the whole turn, up to three times. Once any content has streamed, commit and never retry, because by then the patron has seen something and a retry could contradict it.

## Why none of this appeared in tests

All three were caught live, in a browser, against real services. They weren't caught by the tests, because the tests were written against the world the builder imagined: a tidy event order, a history that included the user's message, and a provider that fails cleanly.

That isn't an accusation. It's what writing your own tests is. You encode your model of the system, and the bugs live where your model is wrong.

## What I changed about "done"

The rule I took from this: the definition of done for every tier includes "verified in a real browser against real services." I don't think a test suite could have replaced that, but I do want it to shrink the gap, which is why the evals in Part 14 exist.

> **Architect's note:** put "verified in a real browser against real services" in every tier's definition of done. The definition of done is the architect's lever, and the agent will hit exactly the bar you set.

I'd like to know how people test streaming UIs. I don't have a good answer for reproducing "events arrive in the order the real provider sends them" without a real provider.

*Part 7 of 18. Next: the attacker never touches my app. They edit a catalog record.*
