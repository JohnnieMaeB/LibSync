---
title: "Integrate with Koha"
date: 2027-02-16
order: 16
unlisted: true
series: Part 16 of 18
---
My plan for connecting LibSync to library catalogs was one line: integrate with Koha. Learning why that was wrong from a web search was a lot cheaper than learning it from a pilot library.

Claude Code's plan was sensible: Supabase for accounts and storage, a Koha connector for the catalog. I asked a question that had nothing to do with code: why Supabase? Then the one that mattered: is this how libraries actually do it? (The ILS I'd actually worked with at a library desk was Sierra, not Koha.) And finally the constraint I care about: I want LibSync integratable with what libraries run right now.

That sent it to research how the rest of the library world connects things. What came back reshaped the roadmap:

Catalogs. Public libraries mostly run Symphony, Polaris, Sierra, Koha or Evergreen. Aspen Discovery reaches each through a separate API driver, so LibSync's connector becomes a driver model: Koha first, Polaris second, SRU as a best-effort fallback. (SRU and Z39.50 are documented for Koha and Alma, not publicly for Sierra or Polaris. Claude's first overview had that wrong.)

Patron login. SIP2 is how e-resource vendors and self-checkout kiosks validate a card and PIN against any ILS. Its sharp edge: replies include personal data whether or not the caller asked, so it must be encrypted, and the integration should keep nothing but "valid or not."

Existing tools. Many libraries run Springshare (LibAnswers, LibChat, LibCal). Its chatbot is deliberately rule-based, so LibSync should complement it.

Law and policy. WCAG 2.1 AA under the ADA Title II rule: April 26, 2027 for populations of 50,000 or more, April 26, 2028 for smaller, after DOJ's April 2026 interim final rule (another claim the first pass had wrong). The Title II rule is less abstract for me: I was a graduate assistant in my university's Accessibility & Disability Services office. ALA's June 2026 AI guidance asks for disclosed AI use, no training on patron data, a library-controlled off switch, and "a clear path to human assistance." That's Part 2's rule written as procurement policy, and it moved trust and compliance ahead of the dashboard.

Supabase survived, since it's invisible infrastructure. Koha-only didn't. This project is also how I'm learning library technology hands-on. SIP2, Aspen and Springshare weren't a syllabus. They're what I ran into when I asked a plan whether it matched the real world, which turns out to be a decent way to learn a field.

Architect's note: an agent optimizes inside the frame you give it. The architect's highest-value move is questioning the frame: "is this how the real world does it?"

Librarians: what did I get wrong?

LibSync build log, Part 16 of 18. Next: the smallest change that makes the data per-library.
