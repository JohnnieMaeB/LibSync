import { useState } from "react";
import { useI18n } from "../i18n";

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
  const { t } = useI18n();
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
            setStatus(t.deleted);
          } catch (error) {
            setStatus((error as Error).message);
          }
          setAsking(false);
        }}
      >
        {t.deleteButton}
      </button>
      <button type="button" className="patron-link" onClick={() => setAsking(false)}>
        {t.cancel}
      </button>
    </div>
  );
}

export function DeviceDataControls({ onClearDevice }: { onClearDevice: () => Promise<void> }) {
  const { t } = useI18n();
  return (
    <ConfirmButton
      label={t.deleteDevice}
      confirmLabel={t.deleteDeviceConfirm}
      onConfirm={onClearDevice}
    />
  );
}
