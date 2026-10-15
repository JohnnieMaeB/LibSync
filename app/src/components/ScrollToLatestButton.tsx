export function ScrollToLatestButton({ hidden, onClick }: { hidden: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      className="scroll-to-latest"
      hidden={hidden}
      onClick={onClick}
    >
      {/* No aria-label: the spoken name must contain the visible text (WCAG
          2.5.3 Label in Name), so voice-control users can say what they see. */}
      <span aria-hidden="true">↓ </span>New messages
    </button>
  );
}
