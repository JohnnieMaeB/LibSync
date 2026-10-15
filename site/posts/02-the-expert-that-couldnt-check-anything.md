---
title: The expert that couldn't check anything
date: 2026-10-20
order: 2
unlisted: true
series: Part 2 of 18
---
In October 2025, my library chatbot's system prompt said: "You are a master of the library's e-book, audiobook, and streaming platforms (e.g., Libby/OverDrive, Kanopy, Hoopla)." That was in my first version, committed by me, before any coding agent had touched the prompt. It had access to none of those platforms.

It answered anyway. Ask whether a book was on Libby and you'd get a fluent, cheerful, invented yes or no. In a demo, a confident answer and a correct one look identical.

The prompt also held something I'm still half proud of: the full text of the RUSA reference-interview guidelines, the ALA Library Bill of Rights and the ALA Core Values, pasted in verbatim. I was a few months into grad school and working a library desk, and encoding the profession's standards was a library-science instinct. The instinct was right. The implementation was 2,300 tokens of pasted documents. Four days later, Google's Jules agent wrapped them in tidy XML tags (primary_instructions, guiding_principles, knowledge_source), which made a pile of text look like architecture. Nobody questioned the size. That includes me.

In July 2026, when I started building with Claude Code, the first document was an audit of what the system actually did, not what the prompt claimed:
- Persona: expertise in several platforms. Data behind it: none. Libby, hoopla and Kanopy have no public API, and OverDrive's are partner-only.
- Retrieval: a Pinecone index of 10 hardcoded policy strings, behind an endpoint that couldn't query them.
- Memory: none. One message in, one reply out.
- Observability: print().

Not a flattering list for a project with "AI" in the pitch. It gave me the rule that has driven every decision since: every answer is grounded in something the system actually retrieved, or it says it doesn't know. A library patron is the wrong person to hand a confident guess.

Architect's note: an agent faithfully implements whatever you put in the prompt, mistakes included. Supplying the domain knowledge is the architect's job. So is questioning how it gets encoded.

What did your first AI prototype claim to know that it couldn't?

LibSync build log, Part 2 of 18. Next: an endpoint that looked finished and could never have worked.
