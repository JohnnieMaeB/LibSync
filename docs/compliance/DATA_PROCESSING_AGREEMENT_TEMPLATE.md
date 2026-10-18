# Data Processing Agreement: Template

> **Not legal advice.** A starting point for a library and a LibSync operator, structured around ALA's Library
> Privacy Guidelines for Vendors and its June 2026 AI guidance. Have the library's counsel adapt it to state law
> (most states protect library records by statute) and to the library's procurement rules.

**Parties:** [Library name] ("Library") and [Operator name] ("Provider"), for the LibSync AI library assistant
("Service").

## 1. Ownership and purpose

1.1 The Library owns all patron data and Library content (policies, FAQs, catalog configuration) processed by the
Service.
1.2 The Provider processes patron data only to operate the Service for the Library, and for no other purpose.

## 2. Data minimization

2.1 The Service collects only what it needs to answer a patron's question. It has no patron accounts, advertising,
analytics trackers or tracking cookies, as described in the LibSync Privacy Notice
(`docs/compliance/PRIVACY_NOTICE.md`), which is incorporated by reference.
2.2 Conversations are held in server memory for no more than [1 hour] of inactivity and are not written to a
database. Diagnostic traces exclude message content.

## 3. AI-specific terms

3.1 Patron messages, Library content and usage data are **not used to train or fine-tune AI models** by the Provider,
and the Provider uses only model providers whose terms prohibit such training.
3.2 The Provider enables zero-data-retention options offered by its model providers where available, and lists
every model provider in Schedule A.
3.3 The Service tells patrons they are using AI, explains its data handling in plain language, and always offers a
path to a human (the Library's chosen "Talk to a librarian" link).
3.4 The Library may switch off any tool group, or the whole Service, at any time.
3.5 The Provider runs and shares the results of regular accuracy evaluations, and notifies the Library of material
changes to models or behavior [10] business days in advance where possible.

## 4. Subprocessors

4.1 Schedule A lists every subprocessor, what it receives, and why. The Provider notifies the Library [30] days before
adding or replacing one, and the Library may object.
4.2 Subprocessors are bound by confidentiality and security obligations no weaker than this Agreement.

## 5. Security

5.1 All data in transit is encrypted (TLS). Credentials the Library provides (e.g. ILS or Springshare API keys) are
stored encrypted and used only for the configured integration.
5.2 The Provider notifies the Library of any security incident affecting Library data within [72 hours] of
discovery.

## 6. Legal requests

6.1 The Provider refers any request for patron data to the Library, discloses data only under a valid court order
or as required by law, and, where lawful, notifies the Library first.

## 7. Accessibility

7.1 The Service conforms to WCAG 2.1 Level AA. The Provider maintains an Accessibility Conformance Report
(`docs/compliance/ACCESSIBILITY_CONFORMANCE_REPORT.md`) and remediates reported issues within [a reasonable period].

## 8. Term, exit and deletion

8.1 On termination, or at any time on request, the Provider deletes Library data (including any uploaded documents
and the Library's search index namespace) within [30] days and confirms in writing.
8.2 The Provider returns Library content in an open format on request before deletion.
8.3 The Library may audit compliance with this Agreement, or accept an equivalent written attestation, once per year.

## Schedule A: Subprocessors (current as of October 2026)

| Subprocessor | Receives | Purpose |
|---|---|---|
| Render | All requests | Server hosting (US) |
| GitHub Pages | Page requests | Static hosting of the patron app and widget |
| Groq | Chat messages | AI inference (primary) |
| Hugging Face Inference Providers (novita) | Chat messages, only when every Groq model is unavailable | AI inference (fallback) |
| Pinecone | Search terms; Library policy documents | Policy search index |
| Open Library, OpenAlex, Crossref | Search terms | Catalog, research, recommendation and citation lookups |
| Supabase | Library settings; staff and email-sign-in accounts; signed-in patrons' synced conversations (keyed by a one-way reference) | Dashboard, sign-in and history sync, only when enabled |
| Logfire (Pydantic) | Diagnostics without message content | Error tracing, if enabled |
