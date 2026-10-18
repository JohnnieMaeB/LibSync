# Piloting LibSync at your library

> **Draft for the project owner to review before sending.** The terms (free for the pilot, eight weeks, deletion on
> request) are proposals, not commitments yet.

LibSync is an AI assistant for your library's website. It answers patrons' questions about your policies, searches
your catalog, recommends books you hold, finds research papers and formats citations, and shows how each answer was
found. This page is what a pilot involves. It is a personal, open-source project, offered free for the pilot.

## What patrons get

- A chat on your website (one `<script>` tag) or as a standalone page, in **English or Spanish**, and answers in the
  language they write in.
- Answers grounded in **your policies** (quoted, never paraphrased into new numbers), **your catalog**, and open
  sources (OpenAlex, Crossref). Book recommendations come only from titles your catalog returns.
- **"How I found this"** under every answer, and a short checklist for judging research sources. You can have both
  open by default ("teach the search").
- **A person, always one step away:** a "Talk to a librarian" link on every screen, offered again automatically if
  the assistant misses twice.
- Optional, if you want them: sign-in with a library card (checked by your ILS over SIP2; LibSync never keeps the
  PIN), "what do I have checked out?", e-book availability (OverDrive), rooms and events (LibCal).

## What your staff get

A dashboard to add your policy documents, connect your catalog (Koha, Polaris or any SRU server), switch features
on and off, see usage (never message text) and today's AI capacity, and create keys for your own AI tools (MCP).
See [ADMIN.md](ADMIN.md).

## What a pilot needs from you

| | Time |
|---|---|
| A staff contact, and the policy pages patrons ask about most (web pages or PDFs) | 1 hour |
| Your catalog's connection details, if you want your own catalog instead of Open Library | 1 hour with IT |
| Paste the embed snippet on a test page, then on your site | 15 minutes |
| A check-in every two weeks, and a few staff asking the assistant hard questions | 30 minutes each |

## A typical eight weeks

1. **Weeks 1–2, set up.** Load policies, connect the catalog, test on a staff-only page. Staff try to break it.
2. **Weeks 3–6, soft launch.** On one page of your site. "Not helpful" reports go to your staff (if you turn it on).
3. **Weeks 7–8, review.** Usage, misses, staff and patron feedback. Keep, change or stop.

**What we'd measure together:** questions answered without staff, answers staff marked wrong, how often patrons
needed a person, and accessibility feedback.

## Privacy and accessibility, in writing

- [Privacy notice](compliance/PRIVACY_NOTICE.md): no chat database, nothing used for AI training, message text kept
  out of diagnostics, and patron accounts optional.
- [Data processing agreement template](compliance/DATA_PROCESSING_AGREEMENT_TEMPLATE.md), for your counsel.
- [Accessibility conformance report](compliance/ACCESSIBILITY_CONFORMANCE_REPORT.md) (WCAG 2.1 AA, VPAT-style). ADA
  Title II deadlines: April 26, 2027 for libraries serving 50,000 or more people, April 26, 2028 for smaller ones.
  The automated audits pass; a manual screen-reader review is planned before launch.

## Honest limits

- It runs on free AI tiers: roughly a thousand questions a day across the service. Fine for a pilot, not yet for a
  large system. The dashboard shows how much is left.
- Integrations other than Koha, SRU and SIP2 (tested weekly against a real Koha) have been tested only against
  their documentation, so a pilot is also the first live test of your vendor connections.
- The Spanish interface was written by the project, not a professional translator; we'd welcome your staff's
  corrections.
- AI can still be wrong. Every answer says what it searched, and staff are a click away.

## Leaving

Remove the script tag and the assistant is gone from your site. On request, your library's settings, documents and
any synced patron history are deleted.
