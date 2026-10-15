---
title: Nothing was deleted
date: 2027-01-12
order: 11
unlisted: true
series: Part 11 of 18
description: My first-ever deployment pipeline run took a static site with exactly one maintainer offline. Nothing was deleted. The site pointed at a branch that never had content.
---
Outages are supposed to be a rite of passage at a company. Mine took down a static site with exactly one maintainer, the first time the new pipeline ran. Nothing was deleted.

## The setup

Claude Code had built per-pull-request previews for the LibSync site. Every PR gets its own URL, so I can look at a change before it merges, which is how I found the bug in Part 1.

The site is hosted on GitHub Pages, which serves one committed tree. So production and previews share a single branch called `gh-pages`: production at the root, each PR under `pr-preview/pr-N/`. Two workflows share it:

- `deploy-pages.yml` publishes production when something is pushed to `main`.
- `pr-preview.yml` publishes a preview when a pull request opens.

## The ordering problem

`deploy-pages.yml` only triggers on a push to `main`, and the workflow files weren't on `main` yet. They were in the PR that introduced them. So the production workflow had never run, and `gh-pages` had never been seeded with a real site.

When the PR opened, `pr-preview.yml` ran. Its fallback logic was: clone `gh-pages`, and if that fails, create a fresh branch with `git init`. The flaw is that it couldn't tell "the branch doesn't exist yet" from any other clone failure.

So it created `gh-pages` from scratch, containing *only* `pr-preview/pr-N/`. No root page at all. GitHub Pages serves a branch's root, so production returned a 404.

`main` was untouched the whole time, and its docs folder was exactly as I'd left it. The site just pointed at a branch that never had any content. That's why this post is called what it is: it's a different kind of outage than data loss, and it's easy to overlook because "I didn't delete anything" is true and unhelpful.

## The same author wrote the flaw and the fix

Claude Code wrote both. The fix has two parts, and the second one is the one worth stealing.

**1. Exactly one workflow may create the branch.** `pr-preview.yml` now runs `git ls-remote --exit-code --heads` to check whether `gh-pages` exists, and if it doesn't, it fails with a clear error instead of creating the branch. `deploy-pages.yml` re-checks on every retry of its push loop, not once up front, because a concurrent run could create the branch in the middle.

**2. Assert the invariant, not the bug.** Both workflows now require that `index.html` exists at the branch root. A preview refuses to publish on top of a broken root, and production refuses to publish a build that doesn't have an `index.html`.

The second fix is worth pausing on. The first one patches the way it broke last time. The second states what must *always* be true about the site, so it catches the next failure too, including ones nobody has imagined: a bad build, a mistaken `rsync` exclude, an empty output folder.

## An echo, months later

The same site returned a 404 again in October, for an unrelated reason. When I made the repository public, the GitHub Pages configuration was removed as a side effect, and the demo went dark until the configuration was restored through the API the same day. Nobody had planned for that. I'm telling you because "fixed" for a deployment pipeline means "fixed for the failures I know about." The invariant check wouldn't have caught that one: `gh-pages` was fine, and Pages simply wasn't pointed at it.

> **Architect's note:** for any pipeline an agent writes, ask "what happens the first time this runs, with nothing else in place?" And when you fix a failure, make the agent assert what must always be true, not just patch what just broke.

What invariant does your deploy pipeline assert?

*Part 11 of 18. Next: every request to my API returned 500 in the browser, and curl said everything was fine.*
