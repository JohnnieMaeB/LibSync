---
title: One script tag
date: 2027-01-26
order: 13
unlisted: true
series: Part 13 of 18
description: Embedding was one script tag. Making that safe took longer, and the safety was in the plan before the code existed.
---
Embedding was one script tag. Making that safe took longer, and the safety was in the plan before the code existed.

## The embed

Libraries add chat tools to their websites by pasting a script tag. They don't run Kubernetes, and many don't have a developer. So the Tier 6 widget is exactly that: a file called `loader.js` with `data-library`, `data-accent` and `data-position` attributes. It adds a floating launcher that opens the assistant.

The difficulty is that I don't control the host page. It might be WordPress, or Drupal, or a decade of accumulated global CSS. So Claude Code built:

- **An iframe.** The host's styles and scripts can't reach the assistant, and mine can't break theirs.
- **A vanilla, zero-dependency loader** with inline styles only: no `<style>` tag and no class names to collide with.
- **A small `postMessage` contract** between the page and the iframe: close and resize.

That part is a pleasant afternoon of engineering. The harder half was on the backend.

## Once anyone can embed it, everyone shares one budget

The moment any site can embed LibSync, all of them spend the same free-tier allowance. A popular library site or a misbehaving one can use up the quota for everyone. So the plan named the abuse limits first:

- **Per-IP limiting** (100 requests per 15 minutes) doesn't model embeds. One embedding site's traffic can come from many patrons on many different IPs, so per-IP limits never add up to a limit on the site. So there's a second limit keyed on the `Origin` header, 500 requests per 15 minutes, which bounds total traffic from a single embed. It's stacked as another `slowapi` decorator on `/agent` and `/chat`, and both limits are checked on every request.
- **An allowlist.** A library registers its id against its origin with `POST /widget/register`. A second origin that tries to claim the same id gets a 409 Conflict. Unregistered origins get a grace quota of 50 requests, so an embed works instantly and then asks you to register.
- **A registry in memory.** Registrations reset when the server cold-starts. That's the $0 tax from Part 10, paid knowingly: a speed bump, not authentication.

I want to be precise about that last point, because it's easy to oversell. An origin allowlist stops casual misuse. It doesn't stop someone who sets headers by hand. Real access control for a library that cares about who can use its assistant is a later problem, and I've written it down as one.

## "Embeddable" means designing for strangers

The phrase hides a lot. It means designing for hosts you'll never see and traffic you don't control, on a budget you can't raise.

## How the plan helped

This is a "what went right" post, and I'd like to say why. The Tier 6 plan, which Claude Code drafted before building, gave abuse its own section and put per-origin rate limiting in the definition of done, so it was a requirement before there was any code. It's much easier to build a rate limit into a design than to bolt one on after someone has already burned your daily quota.

> **Architect's note:** have the agent write the threat model and the definition of done before the code. These abuse limits weren't an afterthought, because the Tier 6 plan named them first. A plan is the cheapest place to catch a design mistake.

If you've built embeddable widgets, what bit you that you didn't expect?

*Part 13 of 18. Next: the day I ran my first real evals, and the score was 0 out of 22.*
