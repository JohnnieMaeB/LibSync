---
title: Two ways a non-answer looked like an answer
date: 2026-11-10
order: 5
unlisted: true
series: Part 5 of 18
---
My agent kept finishing early. Twice, for different reasons, it mistook text that only looked like an answer for the answer. Both came from one line in the design Claude Code and I settled on: output_type=str | BookResult.

Because str is a valid output type, any text the model produces can end the run. Two ways that went wrong, both observed live against Groq:

1. Leaked tool calls. The model sometimes wrote its tool call into the reply instead of issuing one: <function=search_catalog{...}, <search_catalog>{...}</search_catalog>, or raw {"type": "function", "name": "search_catalog", ...} JSON. To the agent that's a perfectly good str, so a patron would have seen the markup.
Fix: an output_validator that matches those patterns and raises ModelRetry, with retries=5 to give the model room to converge on a real tool call.

2. Narration that ended the run. Streaming was built on run_stream(), which commits to the first content matching the output type. A model that says "I'll check the catalog..." before calling a tool had that sentence accepted as the final answer and the tool call dropped.
Fix: run_stream_events(), which runs the whole graph, plus a client that replaces the cumulative text when a new text part starts.

Neither raised an exception. Neither failed a test. Each produced something shaped like a reply, which makes them the most expensive kind of bug. And neither was visible in the code. They only appeared with real model output, which is why "the tests pass" can't be where an architect stops.

Architect's note: review the type signature, not just the logic. Ask "what's the cheapest thing that satisfies this type?" Then feed the agent real traffic, because it designs for the happy path unless you show it the unhappy one.

Where does your agent's output type let a non-answer through?

LibSync build log, Part 5 of 18. Next: the hardest feature to build was a sentence.
