# LibSync Accessibility Conformance Report (draft)

**Format:** modeled on the ITI VPAT® 2.5 (WCAG edition) · **Standard:** WCAG 2.1 Level A and AA, the
technical standard of the ADA Title II web rule · **Report date:** October 2026 · **Status: draft, automated
evaluation only**

Public libraries are state and local government entities, so the ADA Title II rule requires their web content to
meet WCAG 2.1 AA (compliance dates after DOJ's April 2026 interim final rule: April 26, 2027 for populations of
50,000+, April 26, 2028 for smaller ones). A library adopting LibSync will ask for this report. It is honest about
its limits: every "Supports" below is backed by an automated test in this repository, and every criterion that
needs a human judgment is marked **Not Evaluated** until a manual review happens.

## Product

| | |
|---|---|
| Name | LibSync patron chat: the standalone web app and the embeddable widget (`loader.js`) |
| Version | `main` as of October 2026 |
| Interfaces | English and Spanish (the patron's choice, their browser's language, or the library website's) |
| Not covered | The staff dashboard beyond its signed-out view, and the Android/iOS wrappers (Tier 7) |

## Evaluation methods

| Method | Scope | Where |
|---|---|---|
| axe-core 4.x, WCAG 2.1 A/AA rules, in jsdom | Standalone app, widget, privacy dialog | [`app/src/a11y.test.tsx`](../../app/src/a11y.test.tsx), every push |
| axe-core 4.x via Playwright in Chromium, **including color contrast** | Same views plus a reply with book, research and citation cards and the expanded "How I found this" and source checklist; the Spanish interface and its privacy dialog; the staff-handoff card; at 1280×800 and 390×844 | [`app/e2e/a11y.spec.ts`](../../app/e2e/a11y.spec.ts), every push |
| Scripted keyboard tests | Disclosure link → dialog → Escape restores focus; Tab stays inside the open dialog | `app/e2e/a11y.spec.ts`, `app/src/components/AiNotice.test.tsx` |
| **Not yet done** | Manual screen reader testing (NVDA, JAWS, VoiceOver, TalkBack), 200% text resize and 400% zoom/320px reflow, non-text contrast, a cognitive-accessibility review | Planned before a pilot |

Automated tools find a minority of accessibility problems. Treat this report as the floor of what has been verified.

**Fixed during this evaluation:** the citation style selector had no accessible name (4.1.2), the "New messages"
button's spoken name didn't contain its visible text (2.5.3), and the privacy dialog didn't keep keyboard focus
inside it.

## WCAG 2.1 Level A

| Criterion | Conformance | Remarks |
|---|---|---|
| 1.1.1 Non-text Content | Supports | axe `image-alt` passes; book covers and the logo have text alternatives |
| 1.2.1–1.2.3 Time-based media | Not Applicable | No audio or video |
| 1.3.1 Info and Relationships | Supports | axe structure and labeling rules pass, including the citation style selector |
| 1.3.2 Meaningful Sequence | Not Evaluated | Needs a manual reading-order check |
| 1.3.3 Sensory Characteristics | Not Evaluated | Needs manual review of instructions |
| 1.4.1 Use of Color | Partially Supports | Availability badges pair color with text ("lendable"); not manually reviewed elsewhere |
| 1.4.2 Audio Control | Not Applicable | No audio |
| 2.1.1 Keyboard | Partially Supports | Core paths are keyboard-tested (composer, disclosure, dialog); full manual pass pending |
| 2.1.2 No Keyboard Trap | Supports | Escape closes the only modal; focus returns to its opener |
| 2.1.4 Character Key Shortcuts | Supports | The only shortcuts use a modifier (Cmd/Ctrl+K) or Escape |
| 2.2.1 Timing Adjustable | Not Applicable | No time limits for patrons |
| 2.2.2 Pause, Stop, Hide | Supports | Streaming replies can be stopped with the Stop control; no auto-moving content otherwise |
| 2.3.1 Three Flashes | Supports | No flashing content |
| 2.4.1 Bypass Blocks | Supports | axe `region`/`bypass` checks pass; the app is a single view with landmarks |
| 2.4.2 Page Titled | Supports | "LibSync" |
| 2.4.3 Focus Order | Partially Supports | Dialog focus order is tested; full manual pass pending |
| 2.4.4 Link Purpose (In Context) | Supports | axe `link-name` passes; links read "Talk to a librarian", book titles |
| 2.5.1 Pointer Gestures | Supports | No multipoint or path-based gestures |
| 2.5.2 Pointer Cancellation | Supports | Standard buttons activate on click (up-event) |
| 2.5.3 Label in Name | Supports | Fixed in this evaluation (scroll-to-latest button) |
| 2.5.4 Motion Actuation | Not Applicable | No motion input |
| 3.1.1 Language of Page | Supports | `<html lang>` follows the interface language (`en` or `es`) and changes with the language picker; axe passes in both |
| 3.2.1 On Focus | Supports | Focus never changes context |
| 3.2.2 On Input | Supports | Changing citation style only re-formats the citation |
| 3.3.1 Error Identification | Supports | Errors appear as text in the conversation, with a Retry action |
| 3.3.2 Labels or Instructions | Supports | The message box is labeled ("Type your question") |
| 4.1.1 Parsing | Supports | Considered always satisfied for HTML per the 2023 WCAG 2.1 errata |
| 4.1.2 Name, Role, Value | Supports | axe passes after the citation selector fix |

## WCAG 2.1 Level AA

| Criterion | Conformance | Remarks |
|---|---|---|
| 1.2.4–1.2.5 Captions, audio description | Not Applicable | No media |
| 1.3.4 Orientation | Supports | Responsive layout, tested at desktop and phone sizes |
| 1.3.5 Identify Input Purpose | Supports | The optional sign-in fields declare their purpose (`autocomplete="username"`, `current-password`, `email`) |
| 1.4.3 Contrast (Minimum) | Supports | axe color-contrast passes in Chromium on all audited views, including cards |
| 1.4.4 Resize Text | Not Evaluated | 200% text resize not yet tested |
| 1.4.5 Images of Text | Supports | Only the logo, which is exempt |
| 1.4.10 Reflow | Partially Supports | Tested at 390 px wide; 320 px (400% zoom) not yet tested |
| 1.4.11 Non-text Contrast | Not Evaluated | Focus rings and control borders not yet measured |
| 1.4.12 Text Spacing | Not Evaluated | |
| 1.4.13 Content on Hover or Focus | Supports | No hover/focus-triggered content |
| 2.4.5 Multiple Ways | Not Applicable | A single-view application, not a set of pages |
| 2.4.6 Headings and Labels | Supports | axe passes; dialog and app have descriptive headings |
| 2.4.7 Focus Visible | Partially Supports | Visible focus rings since Tier 3; not manually reviewed on every control |
| 3.1.2 Language of Parts | Partially Supports | Each language picker option is marked with its own `lang`. Catalog titles in other languages, and replies the assistant writes in a language other than the interface's, are not marked |
| 3.2.3 Consistent Navigation | Supports | One consistent layout |
| 3.2.4 Consistent Identification | Supports | Controls are named consistently |
| 3.3.3 Error Suggestion | Supports | Error messages say what to do (wait, retry) |
| 3.3.4 Error Prevention (Legal, Financial, Data) | Not Applicable | No such transactions |
| 4.1.3 Status Messages | Supports | A separate status element announces "answering", each search, and the finished reply once, as plain sentences (`lib/announce.ts`). The conversation stays a `role="log"` but is not itself a live region, and is `aria-busy` while a reply streams, so screen readers don't read partial tokens. Changed October 2026 after research on streaming AI output; still to be confirmed with NVDA, JAWS and VoiceOver |

## How to keep this current

**Since the first draft:** the Spanish interface, the language picker (a labelled `<select>`), "How I found this"
and the source checklist (native `<details>` disclosures), and the staff-handoff card (a `role="status"` message) are
in the automated audits above. They still need the manual screen-reader pass.

Re-run `npm test` and `npm run test:e2e` in `app/` (CI does both on every push). Update this report when a
criterion's evidence changes, and record manual review results with the date, tester and assistive technology used.
