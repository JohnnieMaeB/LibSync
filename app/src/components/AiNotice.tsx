import { useState } from "react";
import { PrivacyDialog } from "./PrivacyDialog";

// Always visible, unlike the dismissible capability line: ALA's AI guidance
// (TIER8_PLAN.md §2.8) asks that patrons can always tell they're talking to
// AI, find out what happens to their data, and reach a person.
export function AiNotice({ helpUrl }: { helpUrl: string | null }) {
  const [privacyOpen, setPrivacyOpen] = useState(false);

  return (
    <div className="ai-notice">
      <p>
        You're chatting with an AI assistant. It can make mistakes, so check important details with library
        staff.
      </p>
      <div className="ai-notice-links">
        <button type="button" className="ai-notice-link" onClick={() => setPrivacyOpen(true)}>
          How your data is handled
        </button>
        {helpUrl && (
          <a className="ai-notice-link" href={helpUrl} target="_blank" rel="noopener noreferrer">
            Talk to a librarian
          </a>
        )}
      </div>
      {privacyOpen && <PrivacyDialog helpUrl={helpUrl} onClose={() => setPrivacyOpen(false)} />}
    </div>
  );
}
