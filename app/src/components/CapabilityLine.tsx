import { useI18n } from "../i18n";

export function CapabilityLine({ dismissed, onDismiss }: { dismissed: boolean; onDismiss: () => void }) {
  const { t } = useI18n();
  return (
    <p className={`capability-line${dismissed ? " hidden" : ""}`}>
      {t.capabilityLine}
      <button type="button" className="capability-dismiss" aria-label={t.dismiss} onClick={onDismiss}>
        &times;
      </button>
    </p>
  );
}
