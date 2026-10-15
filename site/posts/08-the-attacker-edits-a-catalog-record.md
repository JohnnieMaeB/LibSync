---
title: The attacker edits a catalog record
date: 2026-12-08
order: 8
unlisted: true
series: Part 8 of 18
description: In my threat model, the attacker never touches my app. They edit a catalog record. An audit found the hole, and the fix was deliberately boring.
---
In my threat model, the attacker never touches my app. They edit a catalog record.

## An audit that found a hole

Tier 3, the interface tier, began with an audit of the existing UI before any new work. Most of what it found was unglamorous: a request to a Google Fonts URL for Segoe UI that 404'd on every page load (Segoe UI is a Microsoft system font, not a Google one), and no visible styling for errors. One finding mattered more than the rest.

Replies were being rendered with `innerHTML`. The model's output was inserted into the page as markup.

## Follow the data

LibSync's tools pull text from sources I don't control: Open Library titles, OpenAlex abstracts, Crossref records, and the policy documents a library uploads. That text goes into the model's context. The model's output goes into the page.

If someone gets an instruction like "reply with `<img src=x onerror=...>`" into any of those sources, an indirect prompt injection becomes a stored cross-site script in my user's browser. They wouldn't need access to my systems at all. Open Library records are community-edited, so "an attacker edits a record" is a short sentence, not a heroic one.

I want to be careful with the claim: this is what *could* have happened. As far as I know, nothing like it ever has. But the audit's job was to find paths, and this was a path.

## The fix is boring, which is the point

- The renderer recognizes exactly three patterns: `**bold**`, `*italic*`, and `[text](https://...)`. The link pattern requires `http` or `https`, so a `javascript:` URL can't match.
- Everything else, matched or not, becomes a plain text node.
- Links open with `target="_blank"` and `rel="noopener noreferrer"`.
- When the frontend moved to React, the rule moved with it: real elements, never `dangerouslySetInnerHTML`.

There's no code path where a string derived from the model can become live markup. That's a stronger statement than "we sanitize the output," because sanitizers are a list of things someone thought to block. An allow-list is a list of things someone chose to permit, and the default is plain text.

## A test that attacks it

The test feeds the renderer exactly what you'd fear:

```html
<img src=x onerror="alert(1)"> <script>alert(2)</script>
```

and asserts two things: there is no `script` element in the resulting DOM, and both strings appear literally, as visible text. If someone later "improves" the renderer in a way that reintroduces markup, that test fails.

## The principle

Model output is untrusted input. Treat it like a form field filled in by an anonymous stranger: escape by default, and allow-list the formatting you actually want. It's easy to forget because the output reads like prose written for you, and it comes from a system you control. The words aren't yours, though. They're a blend of whatever the model was handed, and some of that came from the internet.

## Who found it

Claude Code, in a pass whose only job was to audit. Tier 3 opened with the audit as its own deliverable, before any feature work, and the `innerHTML` line was sitting in the code the tier inherited. Nothing about building features would have sent anyone to that line. A dedicated audit, with its own goal, did. That's the lesson I'd take: asking for an audit as its own task is cheap, and it found something that a feature-focused pass had no reason to look for.

> **Architect's note:** schedule an audit of the agent's work as its own task, with its own goal. An agent that missed a hole while building will often find it in a fresh pass whose only job is to look.

If your app renders LLM output near a DOM, how do you do it? I'd like to compare notes, especially if you've found cases an allow-list like this misses.

*Part 8 of 18. Next: who an interface quietly locks out, and the audit that found my own.*
