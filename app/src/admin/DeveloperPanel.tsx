import { useCallback, useEffect, useState, type FormEvent } from "react";
import type { SupabaseClient } from "@supabase/supabase-js";
import { API_BASE_URL } from "../config";
import type { LibraryRow } from "./AdminApp";

// Tier 8 Phase 34: API keys for the library's own systems, the interactive
// API reference, and an optional webhook for patrons' "not helpful" reports.

interface KeyRow {
  id: string;
  name: string;
  prefix: string;
  created_at: string;
  revoked_at: string | null;
}

export function DeveloperPanel({
  client,
  library,
  accessToken,
}: {
  client: SupabaseClient;
  library: LibraryRow;
  accessToken: string;
}) {
  const [keys, setKeys] = useState<KeyRow[]>([]);
  const [name, setName] = useState("");
  const [newKey, setNewKey] = useState<string | null>(null);
  const [status, setStatus] = useState("");
  const [webhook, setWebhook] = useState(library.feedback_webhook ?? "");
  const [webhookStatus, setWebhookStatus] = useState("");
  const base = `${API_BASE_URL}/admin/libraries/${encodeURIComponent(library.id)}/api-keys`;
  const headers = { Authorization: `Bearer ${accessToken}` };
  const headingId = `developer-${library.id}`;

  const load = useCallback(async () => {
    const response = await fetch(base, { headers }).catch(() => null);
    if (response?.ok) {
      const body = await response.json();
      if (Array.isArray(body)) setKeys(body);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [base, accessToken]);

  useEffect(() => {
    void load();
  }, [load]);

  async function create(event: FormEvent) {
    event.preventDefault();
    const response = await fetch(base, {
      method: "POST",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify({ name: name.trim() || "API key" }),
    }).catch(() => null);
    const body = response ? await response.json().catch(() => ({})) : {};
    if (!response?.ok) {
      setStatus(body.detail ?? "Couldn't create a key.");
      return;
    }
    setNewKey(body.key);
    setName("");
    setStatus("");
    await load();
  }

  async function revoke(key: KeyRow) {
    const response = await fetch(`${base}/${encodeURIComponent(key.id)}`, { method: "DELETE", headers }).catch(() => null);
    setStatus(response?.ok ? `Revoked ${key.name}.` : "Couldn't revoke that key.");
    await load();
  }

  async function saveWebhook(event: FormEvent) {
    event.preventDefault();
    const value = webhook.trim();
    if (value && !value.startsWith("https://")) {
      setWebhookStatus("The webhook must be an https:// address.");
      return;
    }
    const { error } = await client.from("libraries").update({ feedback_webhook: value || null }).eq("id", library.id);
    setWebhookStatus(error ? `Couldn't save: ${error.message}` : value ? "Feedback is on." : "Feedback is off.");
  }

  return (
    <section aria-labelledby={headingId} className="admin-library">
      <h2 id={headingId}>Developers</h2>
      <p>
        Your library's own systems can call LibSync with an API key in an <code>X-LibSync-Key</code> header. See the{" "}
        <a href={`${API_BASE_URL}/docs`} target="_blank" rel="noopener noreferrer">
          interactive API reference
        </a>
        .
      </p>
      <form onSubmit={create}>
        <label htmlFor={`${headingId}-name`}>New key name</label>
        <input id={`${headingId}-name`} value={name} placeholder="Discovery layer" onChange={(e) => setName(e.target.value)} />
        <button type="submit">Create key (admins)</button>
      </form>
      {newKey && (
        <div className="admin-new-key" role="alert">
          <p>Copy this key now. It won't be shown again.</p>
          <pre className="admin-snippet">
            <code>{newKey}</code>
          </pre>
        </div>
      )}
      <p role="status">{status}</p>
      {keys.length > 0 && (
        <ul className="admin-documents">
          {keys.map((key) => (
            <li key={key.id}>
              <span>
                {key.name} <small>({key.prefix}…{key.revoked_at ? ", revoked" : ""})</small>
              </span>
              {!key.revoked_at && (
                <button type="button" className="admin-link-button" onClick={() => revoke(key)}>
                  Revoke<span className="visually-hidden"> {key.name}</span>
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      <h3>Patron feedback</h3>
      <p>
        With a webhook set, patrons in your website's chat can mark an answer "not helpful" and choose to send that
        question and answer to your staff. LibSync forwards it to this address and keeps no copy.
      </p>
      <form onSubmit={saveWebhook}>
        <label htmlFor={`${headingId}-webhook`}>Feedback webhook (https://, leave empty to turn off)</label>
        <input id={`${headingId}-webhook`} value={webhook} onChange={(e) => setWebhook(e.target.value)} />
        <button type="submit">Save webhook</button>
        <p role="status">{webhookStatus}</p>
      </form>
    </section>
  );
}
