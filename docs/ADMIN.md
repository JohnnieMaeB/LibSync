# Staff dashboard and per-library settings (Tier 8)

The staff dashboard lives at `#/admin` on the LibSync site. Library staff sign in with their work Microsoft or
Google account, or an emailed link, and control their library's assistant:

- **Assistant on/off.** When it's off, the widget shows a "Talk to a librarian" panel instead of the chat, and the
  backend refuses chat requests for that library.
- **"Talk to a librarian" link:** a web page, `mailto:` or `tel:`.
- **What the assistant may do:** policies, catalog, research, citations. Switched-off tools are hidden from the
  model.
- **Allowed websites:** only these origins may embed the chat. Leave it empty to allow any.
- **The embed snippet,** ready to paste.
- **LibAnswers FAQs.** Connect LibAnswers under Integrations and press **Sync FAQs now**: your FAQs are copied into
  the assistant's policy knowledge as one document, "LibAnswers FAQs" (each question kept with its answer). Sync
  again after you edit FAQs; each sync replaces the previous copy.
- **Integrations.** Connect OverDrive/Libby (the assistant then reports live copies and holds instead of saying it
  can't check Libby) and Springshare LibCal (it can say which rooms are free on a day and link to your booking page).
  Each needs that vendor's API credentials; the secrets are stored write-only. If the library's "Talk to a
  librarian" link is set, the assistant also offers it whenever it can't help or a patron asks for a person. The
  OverDrive and LibCal connections are written to the vendors' documented APIs but haven't been run against them yet.
- **Developers.** Admins create API keys for the library's own systems (sent as `X-LibSync-Key`; each key is
  shown once and only its hash is stored) and revoke them; a link opens the interactive API reference. A key acts
  for its library without the browser-only checks, but can't use an assistant the library switched off.
- **Patron feedback.** Set an https webhook and patrons in your website's chat get a "Not helpful" option that,
  when they choose it, sends that question and answer to the webhook. LibSync keeps no copy.
- **Usage.** Questions answered, errors and what the assistant looked up, by day, over 7, 30 or 90 days. Counted
  from diagnostic traces, which never contain what patrons wrote. Needs `LOGFIRE_READ_TOKEN` on the backend: a
  Logfire *read* token (Logfire → Settings → Read tokens), separate from the write token used for tracing.
- **Catalog.** Point book search at the library's own catalog: Koha (REST API), Polaris (PAPI) or any SRU server.
  Credentials are stored write-only. If the catalog doesn't answer, LibSync falls back to Open Library and tells the
  patron those results don't show the library's copies. The Koha and Polaris drivers are written to their vendors'
  documented APIs but haven't yet been run against a live server.
- **Policy documents.** Upload PDFs, text, Markdown or HTML (up to 5 MB). The text is split into sections and
  indexed into the library's own search namespace, and from then on the assistant answers policy questions from
  these documents instead of LibSync's sample policies. Uploading a file with the same name replaces it, and
  removing the last document returns the library to the sample policies. **The original file isn't stored**, only
  its text: less data held, per ALA's data-minimization guidance, so keep your own copies. Scanned PDFs without a
  text layer can't be read.

Settings apply within a minute; the backend caches them for 60 seconds. They combine with the embed snippet's
own attributes, and either one can only narrow what the assistant does.

**Until Supabase is configured, all of this is off.** `#/admin` says the dashboard isn't set up, every library
uses the defaults and its snippet attributes, and nothing else changes. If Supabase is down, the backend logs it
and falls back to the same defaults. The chat never fails because of the dashboard.

## One-time setup

1. **Create a Supabase project** (free) at [supabase.com](https://supabase.com).
2. **Create the tables.** Either paste
   each file in [`supabase/migrations/`](../supabase/migrations/), in order, into the Supabase SQL editor, or,
   from the repo root:
   ```bash
   npx supabase login
   npx supabase link --project-ref <your-project-ref>
   npx supabase db push
   ```
   This creates `libraries`, `library_staff` and `library_secrets`, with row-level security, so staff only ever
   see their own library, and integration credentials can be written from the dashboard but never read back.
3. **Backend** (both Render services, under Environment): `SUPABASE_URL` and `SUPABASE_SECRET_KEY`. The secret key
   bypasses row-level security, so it goes on the server only.
4. **Frontend** (GitHub repo variables, not secrets; both are public by design):
   ```bash
   gh variable set VITE_SUPABASE_URL --repo JohnnieMaeB/LibSync
   gh variable set VITE_SUPABASE_PUBLISHABLE_KEY --repo JohnnieMaeB/LibSync
   ```
   The next deploy turns the dashboard on, and the weekly keep-alive starts pinging Supabase so the free project
   doesn't pause.
5. **Sign-in:** in Supabase, under Authentication, set the Site URL to the deployed app
   (`https://johnniemaeb.github.io/LibSync/`) and add `…/LibSync/#/admin` to the redirect URLs. **Turn off "Allow new
   users to sign up"**: staff are invited, never self-registered. For Microsoft and Google sign-in, enable the
   **Azure** and **Google** providers and register LibSync as an app in Microsoft Entra and Google Cloud (Supabase's
   provider pages link the steps). Email links work without that.

## Adding a library and its staff

In the Supabase SQL editor:

```sql
insert into public.libraries (id, name) values ('springfield-pl', 'Springfield Public Library');
```

Invite the staff member under Authentication → Users → Invite. Once they've accepted, make them an admin:

```sql
insert into public.library_staff (library_id, user_id, role)
select 'springfield-pl', id, 'admin' from auth.users where email = 'librarian@springfield.example';
```

Admins can manage settings and credentials. The `id` is the library's `data-library` value in the embed snippet.
