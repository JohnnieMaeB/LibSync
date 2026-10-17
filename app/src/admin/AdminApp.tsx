import { useEffect, useState, type FormEvent } from "react";
import type { Session, SupabaseClient } from "@supabase/supabase-js";
import { getSupabase } from "./supabaseClient";
import { safeHelpUrl } from "../widget";
import { DocumentsPanel } from "./DocumentsPanel";
import { CatalogPanel } from "./CatalogPanel";
import { StatsPanel } from "./StatsPanel";
import { IntegrationsPanel } from "./IntegrationsPanel";

// Tier 8 Phase 30: the staff dashboard at #/admin. Staff sign in with their
// work Microsoft or Google account (or an emailed link), and edit only the
// libraries row-level security lets them see. TIER8_PLAN.md §2.2, §2.8.

export const TOOL_GROUPS = [
  { id: "policies", label: "Library policies" },
  { id: "catalog", label: "Catalog search" },
  { id: "research", label: "Research papers" },
  { id: "citations", label: "Citations" },
  { id: "ebooks", label: "E-book availability (OverDrive, if connected below)" },
  { id: "rooms", label: "Room availability (LibCal, if connected below)" },
] as const;

export interface LibraryRow {
  id: string;
  name: string;
  help_url: string | null;
  enabled_tools: string[] | null;
  ai_enabled: boolean;
  allowed_origins: string[] | null;
  catalog_driver?: string;
  catalog_config?: Record<string, string> | null;
  integrations?: Record<string, Record<string, string>> | null;
}

const LIBRARY_COLUMNS =
  "id,name,help_url,enabled_tools,ai_enabled,allowed_origins,catalog_driver,catalog_config,integrations";

function dashboardUrl(): string {
  return `${window.location.origin}${window.location.pathname}#/admin`;
}

export default function AdminApp({ client = getSupabase() }: { client?: SupabaseClient | null }) {
  return (
    <main className="admin">
      <h1>LibSync staff dashboard</h1>
      {client ? (
        <SignedInGate client={client} />
      ) : (
        <p>
          The staff dashboard isn't set up for this deployment. The operator needs to configure Supabase (see{" "}
          <code>docs/ADMIN.md</code>).
        </p>
      )}
      <p>
        <a href="#/">Back to the chat</a>
      </p>
    </main>
  );
}

function SignedInGate({ client }: { client: SupabaseClient }) {
  const [session, setSession] = useState<Session | null | undefined>(undefined);

  useEffect(() => {
    client.auth.getSession().then(({ data }) => setSession(data.session));
    const { data } = client.auth.onAuthStateChange((_event, next) => setSession(next));
    return () => data.subscription.unsubscribe();
  }, [client]);

  if (session === undefined) return <p role="status">Checking sign-in…</p>;
  if (!session) return <SignIn client={client} />;
  return (
    <>
      <p>
        Signed in as {session.user.email ?? "staff member"}.{" "}
        <button type="button" className="admin-link-button" onClick={() => client.auth.signOut()}>
          Sign out
        </button>
      </p>
      <Libraries client={client} accessToken={session.access_token} />
    </>
  );
}

function SignIn({ client }: { client: SupabaseClient }) {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState("");

  async function sendLink(event: FormEvent) {
    event.preventDefault();
    const { error } = await client.auth.signInWithOtp({
      email,
      // Invite-only: staff accounts are created by the operator, never by sign-up.
      options: { shouldCreateUser: false, emailRedirectTo: dashboardUrl() },
    });
    setStatus(error ? `Couldn't send a link: ${error.message}` : "Check your email for a sign-in link.");
  }

  function withProvider(provider: "azure" | "google") {
    void client.auth.signInWithOAuth({
      provider,
      options: { redirectTo: dashboardUrl(), scopes: provider === "azure" ? "email" : undefined },
    });
  }

  return (
    <section aria-labelledby="sign-in-title">
      <h2 id="sign-in-title">Sign in</h2>
      <div className="admin-actions">
        <button type="button" onClick={() => withProvider("azure")}>
          Sign in with Microsoft
        </button>
        <button type="button" onClick={() => withProvider("google")}>
          Sign in with Google
        </button>
      </div>
      <form onSubmit={sendLink}>
        <label htmlFor="admin-email">Or get a sign-in link by email</label>
        <input
          id="admin-email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <button type="submit">Email me a link</button>
      </form>
      <p role="status">{status}</p>
    </section>
  );
}

function Libraries({ client, accessToken }: { client: SupabaseClient; accessToken: string }) {
  const [libraries, setLibraries] = useState<LibraryRow[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    client
      .from("libraries")
      .select(LIBRARY_COLUMNS)
      .then(({ data, error: loadError }) => {
        if (loadError) setError(loadError.message);
        setLibraries((data as LibraryRow[] | null) ?? []);
      });
  }, [client]);

  if (error) return <p role="alert">Couldn't load your library: {error}</p>;
  if (libraries === null) return <p role="status">Loading your library…</p>;
  if (libraries.length === 0) {
    return <p>Your account isn't linked to a library yet. Ask your LibSync operator to add you.</p>;
  }
  return (
    <>
      {libraries.map((library) => (
        <div key={library.id}>
          <LibrarySettings client={client} library={library} />
          <DocumentsPanel libraryId={library.id} accessToken={accessToken} />
          <CatalogPanel client={client} library={library} />
          <IntegrationsPanel client={client} library={library} />
          <StatsPanel libraryId={library.id} accessToken={accessToken} />
        </div>
      ))}
    </>
  );
}

// Splits the allowed-websites box into origins, rejecting anything that isn't
// a bare http(s) origin (a path or typo would silently block the real site).
export function parseOrigins(text: string): { origins: string[] | null; invalid: string[] } {
  const lines = text
    .split(/\s+/)
    .map((line) => line.trim())
    .filter(Boolean);
  if (lines.length === 0) return { origins: null, invalid: [] };
  const origins: string[] = [];
  const invalid: string[] = [];
  for (const line of lines) {
    try {
      const url = new URL(line);
      if ((url.protocol === "https:" || url.protocol === "http:") && url.origin === line.replace(/\/$/, "")) {
        origins.push(url.origin);
      } else {
        invalid.push(line);
      }
    } catch {
      invalid.push(line);
    }
  }
  return { origins, invalid };
}

function LibrarySettings({ client, library }: { client: SupabaseClient; library: LibraryRow }) {
  const [name, setName] = useState(library.name);
  const [aiEnabled, setAiEnabled] = useState(library.ai_enabled);
  const [helpUrl, setHelpUrl] = useState(library.help_url ?? "");
  const [tools, setTools] = useState<string[]>(library.enabled_tools ?? TOOL_GROUPS.map((t) => t.id));
  const [origins, setOrigins] = useState((library.allowed_origins ?? []).join("\n"));
  const [status, setStatus] = useState("");
  const headingId = `library-${library.id}`;

  async function save(event: FormEvent) {
    event.preventDefault();
    const trimmedHelp = helpUrl.trim();
    if (trimmedHelp && !safeHelpUrl(trimmedHelp)) {
      setStatus("The librarian link must start with https://, http://, mailto: or tel:.");
      return;
    }
    const parsed = parseOrigins(origins);
    if (parsed.invalid.length) {
      setStatus(`These aren't website addresses like https://library.example: ${parsed.invalid.join(", ")}`);
      return;
    }
    const allTools = tools.length === TOOL_GROUPS.length;
    const { error } = await client
      .from("libraries")
      .update({
        name: name.trim() || library.id,
        ai_enabled: aiEnabled,
        help_url: trimmedHelp || null,
        enabled_tools: allTools ? null : tools,
        allowed_origins: parsed.origins,
      })
      .eq("id", library.id);
    setStatus(error ? `Couldn't save: ${error.message}` : "Saved. Patrons see the change within a minute.");
  }

  const snippet = `<script src="${window.location.origin}${window.location.pathname}loader.js" data-library="${library.id}" async></script>`;

  return (
    <section aria-labelledby={headingId} className="admin-library">
      <h2 id={headingId}>{library.name}</h2>
      <form onSubmit={save}>
        <label htmlFor={`${headingId}-name`}>Library name</label>
        <input id={`${headingId}-name`} value={name} onChange={(e) => setName(e.target.value)} />

        <div className="admin-check">
          <input
            id={`${headingId}-ai`}
            type="checkbox"
            checked={aiEnabled}
            onChange={(e) => setAiEnabled(e.target.checked)}
          />
          <label htmlFor={`${headingId}-ai`}>AI assistant is on</label>
        </div>

        <label htmlFor={`${headingId}-help`}>"Talk to a librarian" link (web page, mailto: or tel:)</label>
        <input
          id={`${headingId}-help`}
          value={helpUrl}
          placeholder="https://library.example/ask"
          onChange={(e) => setHelpUrl(e.target.value)}
        />

        <fieldset>
          <legend>What the assistant may do</legend>
          {TOOL_GROUPS.map((tool) => (
            <div className="admin-check" key={tool.id}>
              <input
                id={`${headingId}-tool-${tool.id}`}
                type="checkbox"
                checked={tools.includes(tool.id)}
                onChange={(e) =>
                  setTools((current) =>
                    e.target.checked ? [...current, tool.id] : current.filter((t) => t !== tool.id),
                  )
                }
              />
              <label htmlFor={`${headingId}-tool-${tool.id}`}>{tool.label}</label>
            </div>
          ))}
        </fieldset>

        <label htmlFor={`${headingId}-origins`}>
          Websites allowed to show the chat (one per line; leave empty to allow any)
        </label>
        <textarea
          id={`${headingId}-origins`}
          rows={3}
          value={origins}
          placeholder="https://library.example"
          onChange={(e) => setOrigins(e.target.value)}
        />

        <button type="submit">Save</button>
        <p role="status">{status}</p>
      </form>

      <h3>Embed snippet</h3>
      <p>Paste this into your website, just before the closing &lt;/body&gt; tag:</p>
      <pre className="admin-snippet">
        <code>{snippet}</code>
      </pre>
    </section>
  );
}
