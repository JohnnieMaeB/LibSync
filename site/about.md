---
title: About LibSync
description: What LibSync is, why it exists, and what it isn't yet.
---
LibSync is an AI assistant for public libraries. It answers the kind of questions people ask at a service desk (late fees, renewals, printing, meeting rooms, finding a book, citing a paper) from the library's own policies and from open catalogs, and it says so when it can't check something.

## Why I'm building it

Information being available is not the same as it being accessible. A library can hold the answer and still make it hard to get, and one of the barriers is the social cost of asking a stranger. I want a first question to cost less to ask, with a person always one click away.

It is also how I'm learning library technology hands-on: integrated library systems, SIP2, catalog and discovery APIs, and the standards libraries already run. I have a lot left to learn, so I'm writing the build down in public.

## How it's built

I'm the architect. Claude Code writes nearly all of the current code. The first version, from October 2025, was mine. My job is the part the agent can't see from inside a terminal: the constraints (the whole thing runs on free tiers for $0 a month), what library work is actually like, and noticing when something is wrong.

The [build log](../) records all three threads: what the agent built, what it got wrong, and what I did about it. Some of the mistakes were mine.

The posts here are drafted with Claude's help and edited by me. That is how the code is written too, so it would be odd to hide it.

## What it isn't

- **Not a replacement for librarians.** It is built to hand off to a person.
- **Not audited for accessibility.** It has keyboard support, screen-reader announcements and reduced-motion handling, but no independent audit has happened. A WCAG 2.1 AA audit comes before any pilot.
- **Not in use at any library.** It is a portfolio and learning project. The demo runs on free tiers, so the first message after a quiet spell can take a minute while the backend wakes up.

## Links

- [Live demo](../../)
- [Source code on GitHub](https://github.com/JohnnieMaeB/LibSync) (MIT licensed)
- [Architecture notes](https://github.com/JohnnieMaeB/LibSync/blob/main/ARCHITECTURE.md)
