---
title: The model decides when, code decides what
date: 2026-11-03
order: 4
unlisted: true
series: Part 4 of 18
---
The first time I pinned my citation output in a golden-file test, it caught a bug nobody could fix: "Author, A.& Author, B.." A doubled period and a missing space before the ampersand. That was the official processor's real output.

It's why the model never formats a citation in LibSync. Anyone who's formatted a bibliography by hand knows the rules are fiddly (et al. thresholds, punctuation, page-range dashes, what gets italicized), which is why tools like Zotero exist. So instead of trusting a language model's memory of the rules, Claude Code built the split I'd want from any engineer: the model decides when a citation is needed and which style the patron asked for. Everything else is deterministic.

1. lookup_and_cite(style, doi or title) calls Crossref for the real record.
2. crossref_to_csl_json maps it to CSL-JSON, omitting absent optional fields. citeproc-py renders a None field literally, as "(None)".
3. citeproc-py formats it with the real CSL 1.0.1 style files for APA, MLA or Chicago, the same processor family Zotero uses.
4. The tool returns a ToolReturn whose metadata is a CUSTOM event, and the UI renders a card.

The style switcher calls GET /citation/{doi}?style=chicago and re-runs only the citeproc step against a short-TTL Crossref cache. No second LLM call, no second Crossref lookup.

The other two tools follow the same split: Open Library for books and lending availability, OpenAlex for papers, citation counts and open-access flags. Each returns structured data the model summarizes but can't invent.

The golden-file tests pin the processor's real output, quirk included, and the quirk is documented as known behavior. I'd rather ship a documented imperfection than an invisible guess.

Architect's note: describe the invariant ("a citation must be exactly right"), not the implementation, then favor the design that makes the invariant checkable. Where the rules are exact, make deterministic code the default.

Where should deterministic code have replaced an LLM's judgment in your stack?

LibSync build log, Part 4 of 18. Next: two ways my agent decided it was finished when it wasn't.
