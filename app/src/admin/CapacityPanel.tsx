import { useEffect, useState } from "react";
import { API_BASE_URL } from "../config";

// NEXT_FEATURES.md P2.8: how much of today's free AI budget is left, from the
// rate-limit numbers the AI provider reports on every reply (server
// app/capacity.py). Service-wide, so shown once, not per library. A table,
// like the usage stats, so screen-reader users get the same numbers.

interface ModelCapacity {
  model: string;
  requests_per_day?: number;
  requests_left_today?: number;
  tokens_per_minute?: number | null;
  tokens_left_this_minute?: number | null;
  requests_reset_in?: string | null;
  updated_seconds_ago: number | null;
  throttled_last_hour: number;
}

interface Capacity {
  status: "ok" | "low" | "exhausted" | "unknown";
  primary_model: string;
  models: ModelCapacity[];
}

const STATUS_TEXT: Record<Capacity["status"], string> = {
  ok: "Plenty of AI capacity left today.",
  low: "AI capacity is running low today. When the main model's budget runs out, the assistant switches to backup models until the daily reset.",
  exhausted: "Today's main AI budget is used up. The assistant is using backup models until the daily reset.",
  unknown: "No AI replies since LibSync last restarted, so there's nothing to report yet.",
};

export function CapacityPanel() {
  const [capacity, setCapacity] = useState<Capacity | null>(null);
  const [message, setMessage] = useState("Loading AI capacity…");

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_BASE_URL}/capacity`)
      .then(async (response) => {
        const body = await response.json().catch(() => null);
        if (cancelled) return;
        if (response.ok && body && Array.isArray(body.models) && body.status in STATUS_TEXT) {
          setCapacity(body);
          setMessage("");
        } else {
          setMessage("Couldn't load AI capacity.");
        }
      })
      .catch(() => !cancelled && setMessage("Couldn't reach LibSync."));
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section aria-labelledby="capacity-heading" className="admin-library">
      <h2 id="capacity-heading">AI capacity today</h2>
      {message && <p role="status">{message}</p>}
      {capacity && (
        <>
          <p className={`capacity-status capacity-status--${capacity.status}`}>{STATUS_TEXT[capacity.status]}</p>
          {capacity.models.length > 0 && (
            <table>
              <caption>Per AI model (free tier)</caption>
              <thead>
                <tr>
                  <th scope="col">Model</th>
                  <th scope="col">Requests left today</th>
                  <th scope="col">Resets in</th>
                  <th scope="col">Rate-limited replies, last hour</th>
                </tr>
              </thead>
              <tbody>
                {capacity.models.map((model) => (
                  <tr key={model.model}>
                    <th scope="row">
                      {model.model}
                      {model.model === capacity.primary_model ? " (main)" : ""}
                    </th>
                    <td>
                      {model.requests_left_today != null && model.requests_per_day != null
                        ? `${model.requests_left_today} of ${model.requests_per_day}`
                        : "Not reported"}
                    </td>
                    <td>{model.requests_reset_in ?? "Not reported"}</td>
                    <td>{model.throttled_last_hour}</td>
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
