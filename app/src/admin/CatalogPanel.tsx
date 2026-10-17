import { useState, type FormEvent } from "react";
import type { SupabaseClient } from "@supabase/supabase-js";
import type { LibraryRow } from "./AdminApp";

// Tier 8 Phase 32: point catalog search at the library's own ILS. Non-secret
// settings go in libraries.catalog_config; the credential goes in
// library_secrets, which staff can write but never read back. If the driver
// fails, LibSync falls back to Open Library and tells the patron.

interface DriverSpec {
  id: string;
  label: string;
  fields: { key: string; label: string; placeholder?: string }[];
  secret?: { name: string; label: string };
  note: string;
}

export const DRIVERS: DriverSpec[] = [
  { id: "openlibrary", label: "Open Library (default)", fields: [], note: "Searches the worldwide Open Library catalog." },
  {
    id: "koha",
    label: "Koha (REST API)",
    fields: [
      { key: "base_url", label: "Koha staff interface URL", placeholder: "https://staff.library.example" },
      { key: "client_id", label: "API client ID" },
      { key: "opac_url", label: "OPAC URL for links (optional)", placeholder: "https://catalog.library.example" },
    ],
    secret: { name: "koha_client_secret", label: "API client secret" },
    note: "In Koha, enable RESTOAuth2ClientCredentials, then create an API key under a staff patron's Manage API keys.",
  },
  {
    id: "polaris",
    label: "Polaris (PAPI)",
    fields: [
      { key: "base_url", label: "PAPI service URL", placeholder: "https://papi.library.example/PAPIService/REST" },
      { key: "access_id", label: "PAPI access ID" },
      { key: "org_id", label: "Organization ID (optional, default 1)" },
      { key: "pac_url", label: "PowerPAC URL for links (optional)" },
    ],
    secret: { name: "polaris_access_key", label: "PAPI access key" },
    note: "Needs a Polaris API Service license from Innovative.",
  },
  {
    id: "sru",
    label: "SRU (any catalog with an SRU server)",
    fields: [
      { key: "base_url", label: "SRU endpoint", placeholder: "https://catalog.library.example:9999/biblios" },
      { key: "record_url", label: "Record link template (optional, {id} = record id)" },
      { key: "items_tag", label: 'Item field for availability (optional; "952" for Koha)' },
    ],
    note: "A best-effort option: Koha and Alma document SRU servers. Availability shows only if you set the item field.",
  },
];

export function CatalogPanel({ client, library }: { client: SupabaseClient; library: LibraryRow }) {
  const [driverId, setDriverId] = useState(library.catalog_driver ?? "openlibrary");
  const [settings, setSettings] = useState<Record<string, string>>(library.catalog_config ?? {});
  const [secret, setSecret] = useState("");
  const [status, setStatus] = useState("");
  const driver = DRIVERS.find((d) => d.id === driverId) ?? DRIVERS[0];
  const headingId = `catalog-${library.id}`;

  async function save(event: FormEvent) {
    event.preventDefault();
    const config = Object.fromEntries(
      driver.fields.map((f) => [f.key, (settings[f.key] ?? "").trim()]).filter(([, v]) => v),
    );
    const { error } = await client
      .from("libraries")
      .update({ catalog_driver: driver.id, catalog_config: config })
      .eq("id", library.id);
    if (error) {
      setStatus(`Couldn't save: ${error.message}`);
      return;
    }
    if (driver.secret && secret.trim()) {
      const { error: secretError } = await client
        .from("library_secrets")
        .upsert({ library_id: library.id, name: driver.secret.name, value: secret.trim() });
      if (secretError) {
        setStatus(`Settings saved, but the credential wasn't (admins only): ${secretError.message}`);
        return;
      }
      setSecret("");
    }
    setStatus("Saved. Catalog searches use it within a minute; if it fails, LibSync falls back to Open Library.");
  }

  return (
    <section aria-labelledby={headingId} className="admin-library">
      <h2 id={headingId}>Catalog</h2>
      <form onSubmit={save}>
        <label htmlFor={`${headingId}-driver`}>Search this catalog</label>
        <select id={`${headingId}-driver`} value={driverId} onChange={(e) => setDriverId(e.target.value)}>
          {DRIVERS.map((d) => (
            <option key={d.id} value={d.id}>
              {d.label}
            </option>
          ))}
        </select>
        <p>{driver.note}</p>
        {driver.fields.map((field) => (
          <div key={field.key} className="admin-field">
            <label htmlFor={`${headingId}-${field.key}`}>{field.label}</label>
            <input
              id={`${headingId}-${field.key}`}
              value={settings[field.key] ?? ""}
              placeholder={field.placeholder}
              onChange={(e) => setSettings((s) => ({ ...s, [field.key]: e.target.value }))}
            />
          </div>
        ))}
        {driver.secret && (
          <div className="admin-field">
            <label htmlFor={`${headingId}-secret`}>{driver.secret.label} (stored write-only; leave blank to keep)</label>
            <input
              id={`${headingId}-secret`}
              type="password"
              autoComplete="off"
              value={secret}
              onChange={(e) => setSecret(e.target.value)}
            />
          </div>
        )}
        <button type="submit">Save catalog</button>
        <p role="status">{status}</p>
      </form>
    </section>
  );
}
