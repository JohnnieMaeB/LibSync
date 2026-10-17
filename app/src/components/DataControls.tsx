import { useState } from "react";

// Tier 9 Phase 39: privacy controls (TIER9_PLAN.md §2.3). Destructive actions
// ask once more before acting, and say exactly what will be removed.

export function ConfirmButton({
  label,
  confirmLabel,
  onConfirm,
}: {
  label: string;
  confirmLabel: string;
  onConfirm: () => Promise<void>;
}) {
  const [asking, setAsking] = useState(false);
  const [status, setStatus] = useState("");

  if (!asking) {
    return (
      <div>
        <button type="button" className="patron-link" onClick={() => setAsking(true)}>
          {label}
        </button>
        {status && <p role="status">{status}</p>}
      </div>
    );
  }
  return (
    <div className="data-confirm" role="group" aria-label={label}>
      <p>{confirmLabel}</p>
      <button
        type="button"
        className="data-confirm-yes"
        onClick={async () => {
          try {
            await onConfirm();
            setStatus("Deleted.");
          } catch (error) {
            setStatus((error as Error).message);
          }
          setAsking(false);
        }}
      >
        Delete
      </button>
      <button type="button" className="patron-link" onClick={() => setAsking(false)}>
        Cancel
      </button>
    </div>
  );
}

export function DeviceDataControls({ onClearDevice }: { onClearDevice: () => Promise<void> }) {
  return (
    <ConfirmButton
      label="Delete all conversations on this device"
      confirmLabel="This removes every conversation saved in this browser. It can't be undone."
      onConfirm={onClearDevice}
    />
  );
}
