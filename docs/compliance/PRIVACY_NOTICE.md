# LibSync Privacy Notice

*October 2026. The short version patrons see in the app is the "How your data is handled" dialog
([`PrivacyDialog.tsx`](../../app/src/components/PrivacyDialog.tsx)); this is the full version for libraries and
anyone reviewing LibSync. If the code changes what happens to data, this notice changes in the same pull request.*

LibSync is an AI library assistant. It is written to meet ALA's [Library Privacy Guidelines for
Vendors](https://www.ala.org/advocacy/privacy/guidelines/vendors) and [Guidance on the Use of Artificial
Intelligence in Libraries](https://www.ala.org/tools/standards-and-guidelines/guidance-use-artificial-intelligence-libraries)
(June 2026), and the confidentiality that 48 states and the District of Columbia give library records.

## What patrons share, and where it goes

| Data | Where it goes | Why | How long it is kept |
|---|---|---|---|
| Chat messages | LibSync's server (Render, US) | To run the assistant | In server memory for up to 1 hour of inactivity, then discarded. No chat database |
| Chat messages | AI provider: Groq (primary); Hugging Face Inference Providers (novita) only if all Groq models are unavailable | To write the reply | Groq: not used for training (Groq's services agreement). By default Groq may keep request logs up to 30 days for abuse and reliability monitoring; Zero Data Retention removes that (see the operator checklist). Hugging Face: governed by its and novita's terms |
| Search terms the assistant chooses (not the whole conversation) | Pinecone (policy search); Open Library, OpenAlex, Crossref (books, papers, citations) | To ground answers in real data | Governed by each service's terms; no account or patron identifier is sent |
| Diagnostics (timing, tool names, token counts, errors, `library_id`) | Logfire, if the operator enables tracing | To find and fix failures | Logfire retention. **Message text is excluded** unless `LOGFIRE_INCLUDE_CONTENT` is turned on for local debugging |
| IP address, request metadata | GitHub Pages and Render (hosting) | Delivering the site | Hosting providers' logs |
| One question and answer, **only when the patron chooses "Not helpful"** in a library's chat that collects feedback | The library's own feedback webhook | So staff can follow up and improve answers | LibSync forwards it and keeps no copy; the library's own retention applies |
| Library card number + PIN, **only if the patron chooses to sign in** | The library's own ILS, over SIP2 (encrypted), to check them | To confirm the card belongs to the patron | Neither is stored. LibSync returns an encrypted session token, held in the patron's browser for up to 12 hours, containing a one-way patron reference and the card number (encrypted, readable only by LibSync's server). The PIN is never stored, logged or put in the token |
| Email address, **only if the patron chooses email sign-in** | Supabase Auth | To send a sign-in link | Until the patron's account is deleted |
| Conversation history (standalone app) | The patron's own browser (IndexedDB) | So patrons can return to conversations | Until the patron deletes it from the sidebar or clears site data |

Patron accounts are **optional** and off unless the library enables them. LibSync has **no advertising, no
analytics trackers and no tracking cookies**. The widget on a
library's website keeps nothing after the page is closed. Patrons are asked not to share card numbers, PINs or
other personal details in the chat.

## Library controls

- `data-tools` on the embed snippet turns off tool groups (policies, catalog, research, citations); switched-off
  tools are hidden from the model.
- `data-help-url` sets where "Talk to a librarian" goes.
- Removing the snippet turns the assistant off on that site.

## Patron rights

Patrons can delete their saved conversations at any time from the app's sidebar. Because LibSync keeps no chat
database and no accounts, there is no server-side copy to request, correct or delete beyond the up-to-one-hour
in-memory session, which expires on its own.

## Operator checklist

Things the person running a LibSync deployment must do, because they are account settings rather than code:

- [ ] Enable **Zero Data Retention** in the Groq console (Data Controls). Available on every Groq plan.
- [ ] Keep `LOGFIRE_INCLUDE_CONTENT` unset in production.
- [ ] Decide whether the Hugging Face fallback's retention terms are acceptable; remove it from the chain if not.
