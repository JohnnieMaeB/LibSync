---
title: Who the interface quietly locks out
date: 2026-12-15
order: 9
unlisted: true
series: Part 9 of 18
description: Asking a stranger at a desk for help is a skill, and some of us find it hard. What that means in code, and the accessibility gap an audit found in my own first UI.
---
Asking a stranger at a desk for help is a skill, and some of us find it genuinely hard. I wanted a library you can ask without paying that cost.

## The gap between available and accessible

Libraries run on a promise: information for everyone. But available isn't the same as accessible. Sometimes the barrier isn't a missing book. It's the social cost of asking.

I'm autistic, and for people like me that cost can be the barrier. I've worked a patron desk and I've stood on the other side of one, so I know that cost from both directions. LibSync isn't meant to replace the librarian. It's meant to make the first question cheaper to ask.

## What that means in code

Claude Code built the accessibility baseline in Tier 3, and I told it who it was for. Here is what shipped:

- **A chat log screen readers can hear.** The conversation is a `role="log"` region with `aria-live="polite"`, so new replies are announced instead of silently appearing.
- **Visible keyboard focus on every control, and a keyboard path through the app.** Cmd/Ctrl+K starts a new chat, Esc closes the mobile drawer, and a Stop button works at any moment during a reply.
- **`prefers-reduced-motion` honored** for the streaming cursor, the typing dots and the card animations.
- **No unexplained waiting.** A status pill says what the assistant is doing ("Searching the catalog…"). Errors distinguish "you're sending too fast" from "the service is down," each with a Retry button that doesn't duplicate your message.
- **Starter prompts for people who don't know how to begin,** which disappear after the first message. A blank text box is itself a barrier, because it assumes you know what's worth asking.
- **A system prompt that says:** no assumptions about who's asking, no judgment about what they ask, plain language instead of jargon.

Each of these is small. The point of listing them is that accessibility is made of small decisions, and each one is a place where someone could have been left out.

## The part I didn't expect to write

The Tier 3 audit is the same one that found the injection hole in Part 8. It also found that my first UI had **no visible keyboard focus anywhere**, and a chat log that screen readers never announced.

That is awkward for me to say. I've spent years caring about accessibility, in engineering work and in a university accessibility office, and my own first interface shipped without the basics. I think that's the honest shape of it: caring and building it in are different things, and an audit is what connects them.

## Accessibility without accuracy is a trap

A friendly interface can cause harm if what it says is wrong. An assistant that's easy to ask and confidently wrong is worse than a desk that's hard to approach, because the desk at least doesn't mislead anyone.

That's why the rule from Part 2 matters: grounded, or "I don't know." It's also why ALA's AI guidance insists on a clear path to a human. The goal is a lower first step, with a person always one click away.

## What I can't claim

I haven't had it audited by anyone but me, so I won't call it accessible. Passing my own checks is the weakest form of evidence there is, and it's the same mistake as Part 1 in a different costume: the author and the checker are the same.

A WCAG 2.1 AA audit and a written conformance report come before any pilot. That matters beyond good practice: under the ADA's Title II rule, public entities like libraries have compliance deadlines in April 2027 or 2028, depending on the size of the population they serve. A tool a library puts in front of patrons needs to meet that standard, or the library inherits the problem.

I'd welcome feedback from people who use assistive technology, and from anyone who does accessibility audits for a living. I don't yet know what I'd fail.

> **Architect's note:** an agent will add ARIA attributes the moment you ask. It can't know what being locked out feels like. The architect supplies the lived question ("who can't use this, and why?") and the audit that tests the answer.

Who does your product lock out without anyone noticing?

*Part 9 of 18. Next: running all of this for $0 a month.*
