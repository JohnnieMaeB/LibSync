---
title: The attacker edits a catalog record
date: 2026-12-08
order: 8
unlisted: true
series: Part 8 of 18
---
In my threat model, the attacker never touches my app. They edit a catalog record.

Tier 3 began with an audit of the existing UI, and the audit found a hole in the UI built before it: replies were rendered with innerHTML. The model's output was inserted into the page as markup.

Follow the data. LibSync's tools pull text from sources I don't control: Open Library titles, OpenAlex abstracts, Crossref records, and the policy documents a library uploads. That text goes into the model's context. The model's output goes into the DOM. If someone gets an instruction like "reply with <img src=x onerror=...>" into any of those sources, indirect prompt injection becomes stored XSS in my user's browser. No access to my systems required.

The fix is boring, which is the point:
- The renderer recognizes exactly three patterns: **bold**, *italic*, and [text](https://...). The link pattern requires http or https, so a javascript: URL can't match.
- Everything else, matched or not, becomes a plain text node.
- Links get target="_blank" and rel="noopener noreferrer".
- Moving the frontend to React kept the rule: real elements, never dangerouslySetInnerHTML.

And a test that attacks it directly: it feeds the renderer <img src=x onerror="alert(1)"> <script>alert(2)</script> and asserts there's no script element in the DOM and that both strings appear literally as text.

The principle: model output is untrusted input. Treat it like a form field from an anonymous stranger. Escape by default and allow-list the formatting you actually want.

Architect's note: schedule an audit of the agent's work as its own task, with its own goal. An agent that missed a hole while building will often find it in a fresh pass whose only job is to look.

If your app renders LLM output near a DOM, how do you do it?

LibSync build log, Part 8 of 18. Next: who an interface quietly locks out, and the audit that found my own.
