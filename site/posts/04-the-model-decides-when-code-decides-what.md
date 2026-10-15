---
title: The model decides when, code decides what
date: 2026-11-03
order: 4
unlisted: true
series: Part 4 of 18
description: Why LibSync never lets a language model format a citation, and how a golden-file test caught a bug nobody could fix.
---
The first time I pinned my citation output in a golden-file test, it caught a bug nobody could fix: `Author, A.& Author, B..` A doubled period, and a missing space before the ampersand.

That was the official citation processor's real output. It wasn't a mistake in my code, and I couldn't patch it without lying about what the tool produces.

It's also the reason the model never formats a citation in LibSync.

## Why not just ask the model?

Anyone who has formatted a bibliography by hand knows the rules are fiddly: when "et al." kicks in, where the punctuation goes, how page ranges are dashed, what gets italicized. They differ between APA, MLA and Chicago, and between editions of each. That's why tools like Zotero exist.

A language model has seen a great many citations, so it can produce one that looks right. "Looks right" is the problem. The plan for this tier made the point plainly: the model doesn't reliably know that Chicago uses a different page-range dash than APA, or which style governs "et al." thresholds. With a real style processor, a citation is either right or the style file is missing. With a model, it's plausible-sounding, and plausible-sounding is the hardest kind of wrong to notice.

So the design splits the job. **The model decides *when* a citation is needed and *which style* the patron asked for. Deterministic code does everything else.**

## How the split works

1. **`lookup_and_cite(style, doi or title)`** calls Crossref, the registry where publishers deposit scholarly metadata, for the real record.
2. **`crossref_to_csl_json`** maps that record into CSL-JSON, the structured format citation tools share. It omits optional fields that are absent. That detail is deliberate: `citeproc-py` renders a `None` field literally, so a missing volume number shows up as "(None)" in the output.
3. **`citeproc-py`** formats the record using the real CSL 1.0.1 style files for APA, MLA or Chicago. That's the same processor family Zotero uses.
4. **The tool returns a `ToolReturn`** whose metadata is a custom event, and the interface turns it into a citation card.

The style switcher on the card calls `GET /citation/{doi}?style=chicago` and re-runs only the formatting step. Crossref results are cached for a few minutes, so switching from APA to MLA to Chicago costs no second language-model call and no second lookup.

The other two tools follow the same pattern. Open Library supplies books and lending availability. OpenAlex supplies papers, citation counts and open-access flags. Each returns structured data the model can summarize but can't invent.

## Pinning the quirk

The golden-file tests pin the processor's real output, quirk included. The quirk is written down as known behavior in the demo script rather than patched.

I'm comfortable with that, but I want to be clear about why. If I "fixed" the double period with a string replace, I'd be maintaining a private fork of a citation style in my own code, with my own bugs and no one checking it. If I pin the quirk, I have a test that tells me the moment the upstream processor changes its behavior, and a documented imperfection I can explain. I'd rather ship a documented imperfection than an invisible guess.

I'm less sure that's the right call for a real library. A patron who copies that citation into a paper will carry the double period with them. If you work with students on citations, I'd like to know whether you'd want it fixed at the cost of drifting from the processor.

## What the agent did well here

This is a "what it got right" post, and I want to credit that. Claude Code built the split I'd want from any engineer: the model handles judgment, and exact rules go to code that can be tested. It's also the way around I'd recommend directing an agent. State the invariant ("a citation must be exactly right") and favor the design that makes it checkable, rather than dictating the implementation.

> **Architect's note:** describe the invariant ("a citation must be exactly right"), not the implementation, then favor the design that makes the invariant checkable. Where the rules are exact, make deterministic code the default.

Where should deterministic code have replaced an LLM's judgment in your stack?

*Part 4 of 18. Next: two ways my agent decided it was finished when it wasn't.*
