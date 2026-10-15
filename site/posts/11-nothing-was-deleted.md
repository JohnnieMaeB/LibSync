---
title: Nothing was deleted
date: 2027-01-12
order: 11
unlisted: true
series: Part 11 of 18
---
Outages are supposed to be a rite of passage at a company. Mine took down a static site with exactly one maintainer, the first time the new pipeline ran. Nothing was deleted.

Claude Code had built per-PR previews for a GitHub Pages site. Pages serves one committed tree, so production and previews share a gh-pages branch: production at the root, each PR under pr-preview/pr-N/. Two workflows: deploy-pages.yml publishes production on pushes to main, and pr-preview.yml publishes previews on pull requests.

The ordering problem: deploy-pages.yml only triggers on a push to main, and the workflow files weren't on main yet. It had never run. gh-pages had never been seeded.

pr-preview.yml's fallback was "clone gh-pages; if that fails, git init a fresh branch." It couldn't tell "the branch doesn't exist yet" from any other clone failure. It created gh-pages containing only pr-preview/pr-N/. Pages served that branch's root, and production returned 404. main's docs folder was untouched the whole time. The site just pointed at a branch that never had content.

Claude Code wrote the flaw, and it wrote the fix. Two parts, and the second is the one worth stealing:

1. Exactly one workflow may create the branch. pr-preview.yml now checks git ls-remote --exit-code --heads and hard-fails instead of creating it. deploy-pages.yml rechecks on every retry of its push loop, because a concurrent run can create the branch mid-loop.

2. Assert the invariant, not the bug. Both workflows now require [ -f index.html ] at the branch root. Previews refuse to publish on a broken root, and production refuses to publish a build with no index.html.

Architect's note: for any pipeline an agent writes, ask "what happens the first time this runs, with nothing else in place?" And when you fix a failure, make the agent assert what must always be true, not just patch what just broke.

What invariant does your deploy pipeline assert?

LibSync build log, Part 11 of 18. Next: every request to my API returned 500 in the browser, and curl said everything was fine.
