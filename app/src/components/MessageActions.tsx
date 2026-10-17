import { useState } from "react";

export function MessageActions({
  text,
  onRegenerate,
  onFeedback,
}: {
  text: string;
  onRegenerate?: () => void;
  // Phase 34: only offered when the library collects feedback. The label says
  // exactly what is shared and with whom, so sending is the patron's choice.
  onFeedback?: () => Promise<boolean>;
}) {
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<"idle" | "sending" | "sent" | "failed">("idle");

  const handleFeedback = async () => {
    if (!onFeedback) return;
    setFeedback("sending");
    setFeedback((await onFeedback()) ? "sent" : "failed");
  };

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
      {onFeedback &&
        (feedback === "sent" ? (
          <span className="message-action-note" role="status">
            Sent to library staff. Thank you.
          </span>
        ) : (
          <button
            type="button"
            className="message-action-btn"
            onClick={handleFeedback}
            disabled={feedback === "sending"}
          >
            {feedback === "failed" ? "Couldn't send. Try again" : "Not helpful: send this question and answer to library staff"}
          </button>
        ))}
    </div>
  );
}
