---
title: Who the interface quietly locks out
date: 2026-12-15
order: 9
unlisted: true
series: Part 9 of 18
---
Asking a stranger at a desk for help is a skill, and some of us find it genuinely hard. I wanted a library you can ask without paying that cost.

Libraries run on a promise: information for everyone. But available isn't the same as accessible. Sometimes the barrier isn't a missing book. It's the social cost of asking. I'm autistic, and for people like me that cost can be the barrier. LibSync isn't meant to replace the librarian. It's meant to make the first question cheaper to ask.

What that means in code (Claude Code built it, and I told it who it was for):
- A chat log screen readers can hear: role="log" with aria-live="polite", so new replies are announced instead of silently appearing.
- Visible keyboard focus on every control, and a keyboard path through the app: Cmd/Ctrl+K for a new chat, Esc to close the mobile drawer, a Stop button that works at any moment.
- prefers-reduced-motion honored for the streaming cursor, typing dots and card animations.
- No unexplained waiting. A status pill says what it's doing ("Searching the catalog…"), and errors tell "you're sending too fast" apart from "the service is down," each with a Retry that doesn't duplicate your message.
- Starter prompts for people who don't know how to begin, gone after the first message.
- A system prompt that says: no assumptions about who's asking, no judgment about what they ask, plain language instead of jargon.

Here's the part I didn't expect to write. The Tier 3 audit, the same one that found the XSS hole in Part 8, found that my UI had no visible keyboard focus anywhere, and a chat log screen readers never heard. I've spent years caring about accessibility, in engineering work and in a university accessibility office. Caring isn't the same as building it in. An audit does.

And accessibility without accuracy is a trap. An assistant that's easy to ask and confidently wrong is worse than a desk that's hard to approach. That's why the rule from Part 2 matters (grounded, or "I don't know"), and why ALA's AI guidance insists on a clear path to a human. The goal is a lower first step, with a person always one click away.

I haven't had it audited by anyone but me, so I won't call it accessible yet. A WCAG 2.1 AA audit and a conformance report come before any pilot.

Architect's note: an agent will add ARIA attributes the moment you ask. It can't know what being locked out feels like. The architect supplies the lived question ("who can't use this, and why?") and the audit that tests the answer.

Who does your product lock out without anyone noticing?

LibSync build log, Part 9 of 18. Next: running all of this for $0 a month.
