import { useEffect, useState } from "react";
import { API_BASE_URL } from "../config";

// Tier 8 Phase 33: how patrons use the library's assistant, from Logfire
// traces (never message text). Tables rather than a chart, so the numbers
// are equally available to screen-reader users.

interface LibraryStats {
  days: number;
  turns: number;
  errors: number;
  error_rate: number;
  daily: { day: string; turns: number; errors: number }[];
  tools: { tool: string; calls: number }[];
}

const TOOL_LABELS: Record<string, string> = {
  search_library_policies: "Library policies",
  search_catalog: "Catalog search",
  recommend_books: "Book recommendations",
  check_ebook_availability: "E-book availability",
  check_room_availability: "Room availability",
  check_library_events: "Upcoming events",
  check_my_account: "Patron account lookups",
  search_scholarly_works: "Research papers",
  lookup_and_cite: "Citations",
};

export function StatsPanel({ libraryId, accessToken }: { libraryId: string; accessToken: string }) {
  const [days, setDays] = useState(30);
  const [stats, setStats] = useState<LibraryStats | null>(null);
  const [message, setMessage] = useState("Loading usage…");
  const headingId = `stats-${libraryId}`;

  useEffect(() => {
    let cancelled = false;
    setMessage("Loading usage…");
    fetch(`${API_BASE_URL}/admin/libraries/${encodeURIComponent(libraryId)}/stats?days=${days}`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    })
      .then(async (response) => {
        if (cancelled) return;
        const body = await response.json().catch(() => null);
        if (response.ok && typeof body?.turns === "number" && Array.isArray(body.daily) && Array.isArray(body.tools)) {
          setStats(body);
          setMessage("");
        } else if (response.ok) {
          setStats(null);
          setMessage("Couldn't load usage statistics.");
        } else {
          setStats(null);
          setMessage(body?.detail ?? "Couldn't load usage statistics.");
        }
      })
      .catch(() => !cancelled && setMessage("Couldn't reach LibSync."));
    return () => {
      cancelled = true;
    };
  }, [libraryId, accessToken, days]);

  return (
    <section aria-labelledby={headingId} className="admin-library">
      <h2 id={headingId}>Usage</h2>
      <label htmlFor={`${headingId}-days`}>Period</label>
      <select id={`${headingId}-days`} value={days} onChange={(e) => setDays(Number(e.target.value))}>
        <option value={7}>Last 7 days</option>
        <option value={30}>Last 30 days</option>
        <option value={90}>Last 90 days</option>
      </select>
      {message && <p role="status">{message}</p>}
      {stats && (
        <>
          <dl className="admin-stats">
            <div>
              <dt>Questions answered</dt>
              <dd>{stats.turns}</dd>
            </div>
            <div>
              <dt>Errors</dt>
              <dd>
                {stats.errors} ({(stats.error_rate * 100).toFixed(1)}%)
              </dd>
            </div>
          </dl>
          {stats.tools.length > 0 && (
            <table>
              <caption>What the assistant looked up</caption>
              <thead>
                <tr>
                  <th scope="col">Lookup</th>
                  <th scope="col">Times</th>
                </tr>
              </thead>
              <tbody>
                {stats.tools.map((row) => (
                  <tr key={row.tool}>
                    <th scope="row">{TOOL_LABELS[row.tool] ?? row.tool}</th>
                    <td>{row.calls}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {stats.daily.length > 0 && (
            <table>
              <caption>By day</caption>
              <thead>
                <tr>
                  <th scope="col">Day</th>
                  <th scope="col">Questions</th>
                  <th scope="col">Errors</th>
                </tr>
              </thead>
              <tbody>
                {stats.daily.map((row) => (
                  <tr key={row.day}>
                    <th scope="row">{row.day}</th>
                    <td>{row.turns}</td>
                    <td>{row.errors}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </section>
  );
}
