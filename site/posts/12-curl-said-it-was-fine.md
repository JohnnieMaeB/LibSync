---
title: Curl said it was fine
date: 2027-01-19
order: 12
unlisted: true
series: Part 12 of 18
description: Every request to my API returned 500 in the browser, and curl said everything was fine. Three packages disagreed about what a route is.
---
Every request to my API returned 500 in the browser. `curl` said everything was fine. Three packages disagreed about what a route is.

## Why curl couldn't see it

My frontend (on `github.io`) and my API (on `onrender.com`) live on different origins. Browsers treat that as a security boundary, so before every chat message the browser first sends a **preflight**: an `OPTIONS` request that asks the API, "may this page talk to you?" Only if the answer is yes does the real request go out.

`curl` never sends a preflight. It just makes the request. So from a terminal, the API looked completely healthy while every real user's browser hit a wall.

It had worked fine until observability was switched on.

## The conflict

With a Logfire token set, the app calls `instrument_fastapi()`, which wraps it in OpenTelemetry's FastAPI instrumentation so I can see traces. That instrumentation walks the app's routes and reads a `.path` off each one.

FastAPI 0.137 changed how routes registered through `include_router()` are represented. They're wrapped in a new internal type, `_IncludedRouter`, which has no `.path`. The instrumentation hit one and failed. Every preflight returned a 500, on every route, because every route in my app is registered that way.

A fixed version of the instrumentation exists (`0.64b0`). But it requires a version of `opentelemetry-semantic-conventions` that conflicts with the ceiling that Logfire 4.37.0 puts on `opentelemetry-sdk`. Three packages, each doing something reasonable, with no combination that resolves.

The only available fix was to pin `fastapi<0.137`.

## The comment matters more than the pin

A pinned version isn't interesting. What I'd copy is the comment sitting on top of it in `pyproject.toml`:

- **What breaks, and for whom:** every CORS preflight, so real browsers on a different origin, and no one on `curl`.
- **The exact version chain** that produces the failure.
- **The condition for removing the pin:** when Logfire ships a release compatible with instrumentation 0.64b0 or later.

Beside it, the agent added an entry to the architecture document and a row to the troubleshooting table: *"CORS errors in the browser but not in curl? Check the FastAPI pin."*

## Who that comment is for

It's for a stranger: me, three months from now, after a lot of switching between a job, classes and this project. I won't remember the three package versions. I will remember that something once broke only in browsers, and that is what the troubleshooting row is keyed on.

A solo architect working with an agent gets one chance to leave a trail for that stranger, and the cheapest moment is the one where the problem is still fresh in the agent's context.

## What I haven't done

I haven't checked whether the pin can come off. The condition is written down, and a package release could have satisfied it by now. I'd rather say that than imply the issue is closed. A pin with an exit condition is only useful if someone looks at the exit condition.

> **Architect's note:** make the agent write the exit condition next to every workaround. A workaround without an exit is permanent, and the next session starts without this context.

What's the strangest dependency conflict you've debugged?

*Part 12 of 18. Next: opening the app to every library website on the internet.*
