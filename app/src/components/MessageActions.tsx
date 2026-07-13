import { useState } from "react";

export function MessageActions({
  text,
  onRegenerate,
}: {
  text: string;
  onRegenerate?: () => void;
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(text);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="message-actions">
      <button type="button" className="message-action-btn" aria-label="Copy message" onClick={handleCopy}>
        {copied ? "Copied ✓" : "Copy"}
      </button>
      {onRegenerate && (
        <button
          type="button"
          className="message-action-btn message-action-btn--regenerate"
          aria-label="Regenerate response"
          onClick={onRegenerate}
        >
          Regenerate
        </button>
      )}
    </div>
  );
}
