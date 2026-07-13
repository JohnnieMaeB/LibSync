export function CapabilityLine({ dismissed, onDismiss }: { dismissed: boolean; onDismiss: () => void }) {
  return (
    <p className={`capability-line${dismissed ? " hidden" : ""}`}>
      I can search the catalog, find research papers, and format citations — just ask.
      <button type="button" className="capability-dismiss" aria-label="Dismiss" onClick={onDismiss}>
        &times;
      </button>
    </p>
  );
}
