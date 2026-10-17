import { useState, type FormEvent } from "react";
import type { SupabaseClient } from "@supabase/supabase-js";
import type { LibraryRow } from "./AdminApp";
import { API_BASE_URL } from "../config";

// Tier 8 Phase 37T: services the library already subscribes to. Settings go in
// libraries.integrations; client secrets go in library_secrets (write-only).
// The assistant only gets a vendor's tool when that vendor is filled in here.

interface VendorSpec {
  id: "overdrive" | "libcal" | "libanswers";
  title: string;
  note: string;
  fields: { key: string; label: string; placeholder?: string }[];
  secret: { name: string; label: string };
}

export const VENDORS: VendorSpec[] = [
  {
    id: "overdrive",
    title: "OverDrive / Libby",
    note: "Lets the assistant check live e-book and audiobook availability. Requires OverDrive developer API access.",
    fields: [
      { key: "library_id", label: "OverDrive library ID" },
      { key: "client_id", label: "API client key" },
    ],
    secret: { name: "overdrive_client_secret", label: "API client secret" },
  },
  {
    id: "libcal",
    title: "Springshare LibCal",
    note: "Lets the assistant say which rooms are free on a day. Booking stays on your LibCal page.",
    fields: [
      { key: "site", label: "LibCal site", placeholder: "yourlibrary.libcal.com" },
      { key: "location_id", label: "Location ID" },
      { key: "client_id", label: "API client ID" },
      { key: "booking_url", label: "Booking page URL", placeholder: "https://yourlibrary.libcal.com/reserve" },
    ],
    secret: { name: "libcal_client_secret", label: "API client secret" },
  },
  {
    id: "libanswers",
    title: "Springshare LibAnswers",
    note: "Copies your LibAnswers FAQs into the assistant's policy knowledge. Sync again whenever you change them.",
    fields: [
      { key: "site", label: "LibAnswers site", placeholder: "yourlibrary.libanswers.com" },
      { key: "iid", label: "FAQ group ID (optional)" },
      { key: "client_id", label: "API client ID" },
    ],
    secret: { name: "libanswers_client_secret", label: "API client secret" },
  },
];

function FaqSyncButton({ libraryId, accessToken }: { libraryId: string; accessToken: string }) {
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);

  async function sync() {
    setBusy(true);
    setStatus("Syncing FAQs…");
    const response = await fetch(`${API_BASE_URL}/admin/libraries/${encodeURIComponent(libraryId)}/faq-sync`, {
      method: "POST",
      headers: { Authorization: `Bearer ${accessToken}` },
    }).catch(() => null);
    setBusy(false);
    const body = response ? await response.json().catch(() => ({})) : {};
    setStatus(
      response?.ok
        ? `Synced ${body.faq_count} FAQs. They now appear as "${body.name}" in your documents.`
        : (body.detail ?? "Couldn't reach LibSync. Try again."),
    );
  }

  return (
    <div>
      <button type="button" onClick={sync} disabled={busy}>
        {busy ? "Syncing…" : "Sync FAQs now"}
      </button>
      <p role="status">{status}</p>
    </div>
  );
}

function VendorForm({ client, library, vendor }: { client: SupabaseClient; library: LibraryRow; vendor: VendorSpec }) {
  const [values, setValues] = useState<Record<string, string>>(library.integrations?.[vendor.id] ?? {});
  const [secret, setSecret] = useState("");
  const [status, setStatus] = useState("");
  const idBase = `${library.id}-${vendor.id}`;

  async function save(event: FormEvent) {
    event.preventDefault();
    const settings = Object.fromEntries(
      vendor.fields.map((f) => [f.key, (values[f.key] ?? "").trim()]).filter(([, v]) => v),
    );
    const integrations = { ...(library.integrations ?? {}) };
    if (Object.keys(settings).length) integrations[vendor.id] = settings;
    else delete integrations[vendor.id];
    const { error } = await client.from("libraries").update({ integrations }).eq("id", library.id);
    if (error) {
      setStatus(`Couldn't save: ${error.message}`);
      return;
    }
    library.integrations = integrations; // keep sibling forms from overwriting this one
    if (secret.trim()) {
      const { error: secretError } = await client
        .from("library_secrets")
        .upsert({ library_id: library.id, name: vendor.secret.name, value: secret.trim() });
      if (secretError) {
        setStatus(`Settings saved, but the secret wasn't (admins only): ${secretError.message}`);
        return;
      }
      setSecret("");
    }
    setStatus(Object.keys(settings).length ? "Connected." : "Disconnected.");
  }

  return (
    <form onSubmit={save} aria-labelledby={`${idBase}-title`}>
      <h3 id={`${idBase}-title`}>{vendor.title}</h3>
      <p>{vendor.note}</p>
      {vendor.fields.map((field) => (
        <div key={field.key} className="admin-field">
          <label htmlFor={`${idBase}-${field.key}`}>{field.label}</label>
          <input
            id={`${idBase}-${field.key}`}
            value={values[field.key] ?? ""}
            placeholder={field.placeholder}
            onChange={(e) => setValues((v) => ({ ...v, [field.key]: e.target.value }))}
          />
        </div>
      ))}
      <div className="admin-field">
        <label htmlFor={`${idBase}-secret`}>{vendor.secret.label} (stored write-only; leave blank to keep)</label>
        <input
          id={`${idBase}-secret`}
          type="password"
          autoComplete="off"
          value={secret}
          onChange={(e) => setSecret(e.target.value)}
        />
      </div>
      <button type="submit">Save {vendor.title}</button>
      <p role="status">{status}</p>
    </form>
  );
}

export function IntegrationsPanel({
  client,
  library,
  accessToken,
}: {
  client: SupabaseClient;
  library: LibraryRow;
  accessToken: string;
}) {
  return (
    <section aria-labelledby={`integrations-${library.id}`} className="admin-library">
      <h2 id={`integrations-${library.id}`}>Integrations</h2>
      <p>Connect services your library already uses. Clear a section's fields and save to disconnect it.</p>
      {VENDORS.map((vendor) => (
        <div key={vendor.id}>
          <VendorForm client={client} library={library} vendor={vendor} />
          {vendor.id === "libanswers" && <FaqSyncButton libraryId={library.id} accessToken={accessToken} />}
        </div>
      ))}
    </section>
  );
}
