---
title: One script tag
date: 2027-01-26
order: 13
unlisted: true
series: Part 13 of 18
---
Embedding was one script tag. Making that safe took longer, and the safety was in the plan before the code existed.

Libraries add chat tools by pasting a script tag, so the Tier 6 widget is exactly that: loader.js with data-library, data-accent and data-position attributes. A floating launcher opens the assistant. Libraries paste snippets; they don't run Kubernetes.

I don't control the host page. It's WordPress, or Drupal, or a decade of accumulated global CSS. So Claude Code built:
- An iframe: host styles and scripts can't reach the assistant, and mine can't break theirs.
- A vanilla, zero-dependency loader.js with inline styles only: no style tag, no class names to collide with.
- A small postMessage contract: close and resize.

The harder half was the backend. Once any site can embed LibSync, they all spend one shared free-tier budget.
- Per-IP limiting (100 requests per 15 minutes) doesn't model embeds, where many patrons on different IPs share one site. So there's a second limit keyed on the Origin header, 500 per 15 minutes, stacked as another slowapi decorator on /agent and /chat.
- An allowlist: a library registers its id against its origin with POST /widget/register, and a second origin claiming the same id gets a 409. Unregistered origins get a 50-request grace quota, so an embed works instantly and then asks you to register.
- The registry is in memory, so registrations reset on a cold start. That's the $0 tax from Part 10, paid knowingly: a speed bump, not authentication.

"Embeddable" means designing for hosts you'll never see and traffic you don't control.

Architect's note: have the agent write the threat model and the definition of done before the code. These abuse limits weren't an afterthought, because the Tier 6 plan named them first. A plan is the cheapest place to catch a design mistake.

If you've built embeddable widgets, what bit you that you didn't expect?

LibSync build log, Part 13 of 18. Next: the day I ran my first real evals, and the score was 0 out of 22.
