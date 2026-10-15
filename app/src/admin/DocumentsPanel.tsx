import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { API_BASE_URL } from "../config";

// Tier 8 Phase 31: a library's own policy documents. Uploaded text is indexed
// into the library's search namespace; once it has any, patrons get these
// policies instead of LibSync's shared demo set.

export interface DocumentRow {
  id: string;
  name: string;
  chunk_count: number;
  created_at: string;
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json();
    return body.detail ?? body.error ?? `Request failed (${response.status})`;
  } catch {
    return `Request failed (${response.status})`;
  }
}

export function DocumentsPanel({ libraryId, accessToken }: { libraryId: string; accessToken: string }) {
  const [documents, setDocuments] = useState<DocumentRow[] | null>(null);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const base = `${API_BASE_URL}/admin/libraries/${encodeURIComponent(libraryId)}/documents`;
  const auth = { Authorization: `Bearer ${accessToken}` };
  const headingId = `documents-${libraryId}`;

  const load = useCallback(async () => {
    const response = await fetch(base, { headers: auth }).catch(() => null);
    if (!response?.ok) {
      setStatus(response ? await errorMessage(response) : "Couldn't reach LibSync. Try again.");
      setDocuments([]);
      return;
    }
    setDocuments(await response.json());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [base, accessToken]);

  useEffect(() => {
    void load();
  }, [load]);

  async function upload(event: FormEvent) {
    event.preventDefault();
    const file = fileRef.current?.files?.[0];
    if (!file) {
      setStatus("Choose a file first.");
      return;
    }
    setBusy(true);
    setStatus(`Uploading ${file.name}…`);
    const form = new FormData();
    form.append("file", file);
    const response = await fetch(base, { method: "POST", headers: auth, body: form }).catch(() => null);
    setBusy(false);
    if (!response?.ok) {
      setStatus(response ? await errorMessage(response) : "Couldn't reach LibSync. Try again.");
      return;
    }
    const result = await response.json();
    setStatus(`Added ${result.name} (${result.chunk_count} sections). Patrons can ask about it within a minute.`);
    if (fileRef.current) fileRef.current.value = "";
    await load();
  }

  async function remove(doc: DocumentRow) {
    const response = await fetch(`${base}/${encodeURIComponent(doc.id)}`, { method: "DELETE", headers: auth }).catch(
      () => null,
    );
    setStatus(response?.ok ? `Removed ${doc.name}.` : "Couldn't remove it. Try again.");
    await load();
  }

  return (
    <section aria-labelledby={headingId} className="admin-library">
      <h2 id={headingId}>Policy documents</h2>
      <p>
        Upload your library's policies (PDF, text, Markdown or HTML, up to 5 MB). The assistant answers policy
        questions from these. Uploading a file with the same name replaces it. The original file isn't stored, only
        its text.
      </p>
      <form onSubmit={upload}>
        <label htmlFor={`${headingId}-file`}>Document</label>
        <input id={`${headingId}-file`} ref={fileRef} type="file" accept=".pdf,.txt,.md,.html,.htm" />
        <button type="submit" disabled={busy}>
          {busy ? "Uploading…" : "Upload"}
        </button>
      </form>
      <p role="status">{status}</p>
      {documents === null ? (
        <p>Loading documents…</p>
      ) : documents.length === 0 ? (
        <p>No documents yet. Until you add some, the assistant uses LibSync's sample policies.</p>
      ) : (
        <ul className="admin-documents">
          {documents.map((doc) => (
            <li key={doc.id}>
              <span>
                {doc.name} <small>({doc.chunk_count} sections)</small>
              </span>
              <button type="button" className="admin-link-button" onClick={() => remove(doc)}>
                Remove<span className="visually-hidden"> {doc.name}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
