# LibSync — What to Build Next (research, October 2026)

Tiers 1–9 are built. Everything that needs an outside account is **off until configured** and falls back to
today's behavior, and several integrations have only been tested with mocks. This document collects research on
what libraries need now and ranks the next features. Sources are linked inline; vendor claims are labeled as such.

## Where LibSync stands

| Area | State |
|---|---|
| Patron chat (web, widget, Android/iOS) | Live; WCAG 2.1 AA automated checks on every push |
| Grounding | Policy RAG, catalog, research, citations; book answers carry the catalog's exact facts (#67) |
| Staff dashboard, documents, ILS drivers, stats, vendor tools, API keys | Built; **off until Supabase etc. are configured** |
| Patron accounts (SIP2 card, email), synced history, account lookups | Built; **off until `PATRON_SESSION_SECRET`** |
| Verified live | SRU (Library of Congress and Koha), Koha REST, SIP2 (Koha), Pinecone indexing, the production chat |
| **Verified only with mocks** | Polaris PAPI, OverDrive, LibCal, LibAnswers, Supabase, Logfire queries |

## What the research says

**1. Libraries are cautious, and their worry is patrons' thinking, not the technology.** Clarivate's *Pulse of the
Library 2026* found many libraries still building AI governance, with reported adoption around 16% globally and 11%
in the U.S. (Clarivate sells library AI products, so read the figures with that in mind)
([Clarivate](https://clarivate.com/pulse-of-the-library/),
[review](https://www.mastersinlibraryscience.org/articles/ai-adoption-in-libraries-2026-10-01/)). In a *Library
Journal* staff survey (late draft), 55% of respondents who discussed patrons worried about patrons losing critical
thinking or information literacy, and 43% about misinformation
([Library Journal](https://www.libraryjournal.com/story/technology/ai-defiance)). The PLA's AI work centers on
"listening first" and what has to be true before patrons trust a library AI tool
([PLA](https://www.ala.org/pla/initiatives/ai)), and ALA published guidance on AI policies in July 2026
([ALA](https://www.ala.org/news/2026/07/ala-special-report-surveys-generative-ai-policies-public-and-academic-libraries)).

**2. The leading vendor tool has accessibility gaps.** Ex Libris's Primo Research Assistant (RAG over the Central
Discovery Index) is reviewed as having screen-reader and keyboard gaps, plus outdated results and occasional
inaccurate summaries ([Choice 360](https://www.choice360.org/libtech-insight/ai-tools-for-academic-libraries-ai-research-assisants/),
[Ex Libris](https://exlibrisgroup.com/announcement/ex-libris-launches-a-beta-program-of-generative-ai-powered-primo-research-assistant/)).
I found nothing on a Springshare AI launch; its LibAnswers chatbot remains rule-based. Public-library chat
specifically is thinly served: most offerings are academic or generic.

**3. Hallucination is still the core risk, and there are small, open checks for it.** Open detectors include
Vectara's HHEM-2.1-Open (Apache 2.0, about 110M parameters, under 600 MB RAM, about 1.5 s per 2k tokens on CPU;
about 67% balanced accuracy on adversarial FaithBench)
([model card](https://huggingface.co/vectara/hallucination_evaluation_model)), LettuceDetect
([paper](https://arxiv.org/pdf/2502.17125)) and MiniCheck; RAGAS and DeepEval are LLM-judge frameworks better suited
to CI ([roundup](https://www.giskard.ai/knowledge/the-best-hallucination-detection-tools-for-llms-and-ai-agent-2026)).
Render's free instance has 512 MB of RAM, so even HHEM can't run alongside the server there. In production LibSync
has said renewals are "up to 2 additional periods" when the policy says three, and has added details that aren't in
the retrieved text: the open problem these tools address.

**4. Readers' advisory is a core library service that general chatbots do badly.** NoveList (EBSCO) argues that
chatbots are a poor fit for book recommendations, partly because it's hard to make them recommend only books in the
library's collection ([NoveList](https://about.ebsco.com/blogs/novelist/how-spark-joy-readers-without-ai-chatbots)).
LibSync can do exactly that: its catalog drivers know what this library holds.

**5. Language access is underserved.** I found no 2026 evaluation of chatbots serving English learners in U.S.
public libraries; the nearest example is a Finnish public-library chatbot that answers in the patron's language
(vendor claims) ([Biblioworks](https://biblioworks.ai/products/ai-library-chatbot/)). ALA has a toolkit for serving
multilingual communities ([ALA](https://www.ala.org/sites/default/files/advocacy/content/Engaging%20Multilingual%20Communities%20and%20English%20Language%20Learners%20in%20U.S.%20Libraries%20%20Toolkit_1.pdf)).

**6. The free tier is the scaling ceiling.** Groq's free plan gives gpt-oss-120b about 30 requests/minute,
1,000/day, 8,000 tokens/minute and 200,000 tokens/day, per organization
([benchlm](https://benchlm.ai/free-tier/groq), [klymentiev](https://klymentiev.com/blog/groq-pricing)); this matches
what LibSync measured. Cerebras's free credit now needs a payment method, and OpenRouter's free models allow about
50 requests/day ([OpenRouter](https://openrouter.ai/blog/tutorials/free-llm-apis-compared/)). With three Groq models in
the chain, LibSync handles roughly 1,000 patron turns a day: fine for a pilot, not for a large system.

**7. MCP is now mainstream.** The official MCP registry listed about 9,600 servers in May 2026 (third-party count)
([analysis](https://www.digitalapplied.com/blog/mcp-adoption-statistics-2026-model-context-protocol)). No library
catalog or policy MCP servers turned up.

## Recommended next steps, ranked

### P0: make what exists trustworthy and real

1. ✅ **Policy grounding guard** (closes the known embellishment problem). *Built: `app/grounding.py` plus an
   output validator and a prompt rule, plus HHEM-2.1-Open as a weekly faithfulness score (`evals/faithfulness.py`).*
   - A deterministic check that every number, price and duration in a policy answer appears in the retrieved
     policy text, the same approach as the book guard in #67. On a mismatch, the model retries.
   - A prompt rule: say only what the policy says, and suggest staff for anything else.
   - New eval cases for each embellishment seen in production.
   - HHEM-2.1-Open as an **offline** eval metric in the weekly run, not in production (RAM).
2. ✅ **Verify the integrations against real systems, at $0, in CI.** *Built for Koha: a weekly workflow
   (`koha-live.yml`) runs the Koha REST, SRU and SIP2 drivers against koha-testing-docker. It found two SIP2
   bugs the mocks hid (CR LF replies; one item list per request) and that Koha lists barcodes, not titles. Polaris
   needs its free Developer Network sandbox, which needs your sign-up.*
3. **Switch on the operator settings** (yours): Supabase, Groq Zero Data Retention, `PATRON_SESSION_SECRET`, a
   Logfire read token. Then a manual screen-reader pass (NVDA, VoiceOver) to finish the conformance report.

### P1: what libraries are asking for

4. **Information literacy mode.** This answers librarians' top concern directly. Every grounded answer can show how
   it was found ("I searched the catalog for…; these came from the library's policies"), and research answers can
   offer a short evaluation prompt in the RUSA tradition (who wrote it, when, is it peer reviewed, lateral reading).
   A library could make "teach the search" the default.
5. **Readers' advisory grounded in the collection.** "Books like X" and "something for a 10-year-old who loves
   dragons", answered only with titles the library holds, through the catalog drivers, with subjects from Open
   Library. This is NoveList's critique of chatbots, turned into a feature.
6. **Language access.**
   - ✅ Answer in the patron's language: a prompt rule, Spanish number words in the number check, and eval cases
     in Spanish and Chinese.
   - Translate the interface, starting with Spanish.
   - ✅ Measured policy retrieval across languages (`evals/multilingual_retrieval.py`): the expected policy was in
     the top 3 for 79 of 80 questions across English, Spanish, Chinese, Vietnamese, Tagalog, Arabic, Korean and
     Russian. The one miss was a Vietnamese question about visual-impairment services.

### P2: reach and resilience

7. **A LibSync MCP server.** Expose catalog search, policy search and citations as MCP tools, so library staff can
   use them from their own AI tools. It's cheap to build with the existing tools.
8. **Capacity and budget visibility.** Surface Groq request and token headroom in the stats panel (the Tier 8 plan
   called for it), alert before the daily cap, and add OpenRouter's free models as one more fallback.
9. **Pilot kit.** A demo library seeded in Supabase, a one-page onboarding guide, a sample procurement packet
   (conformance report, privacy notice, data agreement) and outreach through Code4Lib.

### Decisions only you can make
- **Tier 7 Phase 29:** publish to the App Store ($99/year) and Google Play ($25 once)?
- **Pilot library:** which library to approach first, and when.
