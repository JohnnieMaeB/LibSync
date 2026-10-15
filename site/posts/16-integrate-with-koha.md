---
title: "Integrate with Koha"
date: 2027-02-16
order: 16
unlisted: true
series: Part 16 of 18
description: My plan for connecting LibSync to library catalogs was one line, and learning why it was wrong from a web search was far cheaper than learning it from a pilot library.
---
My plan for connecting LibSync to library catalogs was one line: *integrate with Koha.* Learning why that was wrong from a web search was a lot cheaper than learning it from a pilot library.

## The questions that weren't about code

Claude Code's plan was sensible. Supabase for accounts and storage, and a Koha connector for the catalog. Koha is open source with a documented REST API, so it's realistic to test against.

I asked a question that had nothing to do with code: *why Supabase?* Then the one that mattered: *is this how libraries actually do it?* The ILS I'd actually worked with behind a library desk was Sierra, not Koha. And finally, the constraint I care about: I want LibSync to be integratable with what libraries are running right now.

That sent Claude Code off to research how the rest of the library world connects its systems. What came back reshaped the roadmap.

## What it found

**Catalogs.** Public libraries mostly run Symphony, Polaris, Sierra, Koha or Evergreen. Aspen Discovery, a widely used open-source discovery layer, reaches each of them through a separate API driver. So LibSync's connector became a driver model: Koha first, Polaris second, and SRU only as a best-effort fallback. SRU and Z39.50 are publicly documented for Koha and Alma, but not for Sierra or Polaris. The first overview Claude Code gave me got that wrong, and said they were nearly universal.

**Patron login.** SIP2 is how e-resource vendors and self-checkout kiosks validate a library card and PIN against any ILS. Its sharp edge: replies include personal data whether or not the caller asked for it. So it must be encrypted, and the integration should keep nothing except "valid or not."

**Existing tools.** Many libraries already run Springshare (LibAnswers, LibChat and LibCal). Its chatbot is deliberately rule-based, not AI. So LibSync should complement it: LibAnswers FAQs as a source of policies, LibChat as the human handoff, and LibCal for real room availability.

**Law and policy.** Public libraries are state or local government, so the ADA's Title II rule applies, and it requires WCAG 2.1 AA. After the Department of Justice's April 2026 interim final rule, compliance is due **April 26, 2027** for populations of 50,000 or more, and **April 26, 2028** for smaller ones. The first pass had that wrong too, with deadlines starting in 2026.

The Title II rule is less abstract to me than it might be. I was a graduate assistant in my university's Accessibility & Disability Services office.

ALA's June 2026 *Guidance on the Use of AI in Libraries* asks for disclosed AI use, no training on patron data, a library-controlled off switch, and "a clear path to human assistance." That is Part 2's rule written as procurement policy. It moved trust and compliance ahead of the dashboard in the roadmap.

## What survived

Supabase survived, because it's invisible infrastructure: a library never touches it. The "Koha only" plan didn't. The principle that came out of it is that LibSync's own infrastructure can be anything cheap, but everything a library *touches* should be a system it already runs.

## Learning by asking the plan a question

This project is also how I'm learning library technology hands-on. SIP2, Aspen and Springshare weren't a syllabus I followed. They're what I ran into when I asked a plan whether it matched the real world, which turns out to be a decent way to learn a field.

I also want to be straight about the limits of this research. It's desk research done in October 2026 by an agent, with sources cited in the plan, and it hasn't been tested against a real library's setup. I haven't built the Koha or Polaris drivers yet. Regulations change, and the ADA dates especially need re-checking before anyone relies on them.

> **Architect's note:** an agent optimizes inside the frame you give it. The architect's highest-value move is questioning the frame: "is this how the real world does it?"

Librarians: what did I get wrong?

*Part 16 of 18. Next: the smallest change that makes the data per-library.*
