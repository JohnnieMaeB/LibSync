import { useState } from "react";
import { PrivacyDialog } from "./PrivacyDialog";
import { useI18n } from "../i18n";

// Always visible, unlike the dismissible capability line: ALA's AI guidance
// (TIER8_PLAN.md §2.8) asks that patrons can always tell they're talking to
// AI, find out what happens to their data, and reach a person.
export function AiNotice({ helpUrl }: { helpUrl: string | null }) {
  const { t } = useI18n();
  const [privacyOpen, setPrivacyOpen] = useState(false);

  return (
    <div className="ai-notice">
      <p>{t.aiNotice}</p>
      <div className="ai-notice-links">
        <button type="button" className="ai-notice-link" onClick={() => setPrivacyOpen(true)}>
          {t.dataHandling}
        </button>
        {helpUrl && (
          <a className="ai-notice-link" href={helpUrl} target="_blank" rel="noopener noreferrer">
            {t.talkToLibrarian}
          </a>
        )}
      </div>
      {privacyOpen && <PrivacyDialog helpUrl={helpUrl} onClose={() => setPrivacyOpen(false)} />}
    </div>
  );
}
