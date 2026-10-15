---
title: Curl said it was fine
date: 2027-01-19
order: 12
unlisted: true
series: Part 12 of 18
---
Every request to my API returned 500 in the browser. curl said everything was fine. Three packages disagreed about what a route is.

My frontend (github.io) and API (onrender.com) are different origins, so every chat message starts with a CORS preflight, an OPTIONS request. It worked until observability was switched on.

With LOGFIRE_TOKEN set, instrument_fastapi() wraps the app in OpenTelemetry's FastAPI instrumentation. FastAPI 0.137 changed how routes registered through include_router() are represented, wrapping them in a new _IncludedRouter type. The instrumentation reads .path off each route, the new type doesn't have one, and every preflight 500s, on every route, because every route in my app is registered that way. curl never sends a preflight, which is why the API looked healthy from a terminal.

A fixed instrumentation release exists (0.64b0). It requires opentelemetry-semantic-conventions==0.64b0, which conflicts with logfire 4.37.0's own opentelemetry-sdk<1.43.0 ceiling. No upgrade path resolved. The only available fix: pin fastapi<0.137.

The pin isn't the part to copy. The comment on it is: what breaks and for whom (real browsers, cross-origin), the exact version chain, and the condition for removing it (when logfire ships a release compatible with instrumentation 0.64b0 or later). Plus an architecture-doc entry and a troubleshooting row: "CORS errors in the browser but not in curl? Check the FastAPI pin."

That comment is for a stranger: me in three months, after a lot of context switching between jobs, classes and this project. A solo architect working with an agent gets one chance to leave a trail for that stranger.

Architect's note: make the agent write the exit condition next to every workaround. A workaround without an exit is permanent, and the next session starts without this context.

What's the strangest dependency conflict you've debugged?

LibSync build log, Part 12 of 18. Next: opening the app to every library website on the internet.
