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

Settings apply within a minute; the backend caches them for 60 seconds. They combine with the embed snippet's
own attributes, and either one can only narrow what the assistant does.

**Until Supabase is configured, all of this is off.** `#/admin` says the dashboard isn't set up, every library
uses the defaults and its snippet attributes, and nothing else changes. If Supabase is down, the backend logs it
and falls back to the same defaults. The chat never fails because of the dashboard.

## One-time setup

1. **Create a Supabase project** (free) at [supabase.com](https://supabase.com).
2. **Create the tables.** Either paste
   [`supabase/migrations/20261015000000_tenancy.sql`](../supabase/migrations/20261015000000_tenancy.sql) into the
   Supabase SQL editor, or, from the repo root:
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
