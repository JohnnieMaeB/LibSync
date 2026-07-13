import { useState } from "react";
import { API_BASE_URL } from "../config";
import type { CitationCardData } from "../types";
import { SourceBadge } from "./SourceBadge";

// Renders a citation CUSTOM event payload as a citation card: formatted
// text, a copy-to-clipboard button, and a style switcher that re-formats via
// GET /citation/{doi} instead of re-running the whole lookup_and_cite tool call.
export function CitationCard({ data, number }: { data: CitationCardData; number: number }) {
  const [formatted, setFormatted] = useState(data.formatted);
  const [style, setStyle] = useState(data.style);
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(formatted);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const handleStyleChange = async (nextStyle: string) => {
    setStyle(nextStyle);
    if (!data.doi) return;
    try {
      const response = await fetch(`${API_BASE_URL}/citation/${data.doi}?style=${encodeURIComponent(nextStyle)}`);
      if (!response.ok) return;
      const payload = await response.json();
      setFormatted(payload.formatted);
      setStyle(payload.style);
    } catch {
      // Network hiccup: leave the previously formatted text in place.
    }
  };

  const showStyleSwitcher = data.doi && data.availableStyles && data.availableStyles.length > 1;

  return (
    <div className="citation-card">
      <SourceBadge number={number} />
      <p className="citation-card-text">{formatted}</p>
      <div className="citation-card-controls">
        <button type="button" className="citation-card-copy" onClick={handleCopy}>
          {copied ? "Copied!" : "Copy"}
        </button>
        {showStyleSwitcher && (
          <select
            className="citation-card-style-select"
            value={style}
            onChange={(e) => handleStyleChange(e.target.value)}
          >
            {data.availableStyles!.map((s) => (
              <option key={s} value={s}>
                {s.toUpperCase()}
              </option>
            ))}
          </select>
        )}
      </div>
    </div>
  );
}
