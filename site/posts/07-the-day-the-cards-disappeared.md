---
title: The day the cards disappeared
date: 2026-12-01
order: 7
unlisted: true
series: Part 7 of 18
---
The book card appeared for a split second, then vanished. Every unit test was green. They'd been written against an event order that happened not to trigger the bug.

LibSync streams over AG-UI, an event protocol for agent-to-frontend communication. Claude Code and I picked it over MCP Apps: my frontend is first-party and already trusts my backend, and MCP Apps solves rendering a stranger's tool UI in a sandbox, which isn't my problem. /agent sits beside /chat, so a bug in the new transport can't take down the old one. A tool becomes a card by returning ToolReturn(return_value=..., metadata=CustomEvent(...)); search_catalog emits one CUSTOM book_card per result, live.

Then three bugs that only a real browser, a real conversation and a real provider could produce:

1. Vanishing cards. The real event order is TOOL_CALL_RESULT, then CUSTOM (the card), then TEXT_MESSAGE_CONTENT (the narration). The handler cleared the bubble on every text event, wiping the card. Fix: clear the placeholder once, on whichever event arrives first.

2. Amnesia from turn two. AGUIAdapter folds the user's new message into message_history before the run, so result.new_messages() never contains it. Persisting only that dropped every user turn. Fix: store history + the request's messages + new_messages().

3. Raw provider errors. Groq's tool_use_failed escaped FallbackModel, which guards stream entry, not iteration of a stream already handed back. About two in three attempts at "Find me a sci-fi audiobook" failed (yes, Part 1's prompt). Fix: buffer events until the first non-RUN_STARTED one; on a RUN_ERROR before real content, discard and retry the whole turn, up to three times. Never retry once content has streamed.

All three were caught live in a browser, not by the tests, because the tests were written against the world the builder imagined.

Architect's note: put "verified in a real browser against real services" in every tier's definition of done. The definition of done is the architect's lever, and the agent will hit exactly the bar you set.

LibSync build log, Part 7 of 18. Next: the attacker never touches my app. They edit a catalog record.
