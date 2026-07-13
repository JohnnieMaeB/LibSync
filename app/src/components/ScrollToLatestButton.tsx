export function ScrollToLatestButton({ hidden, onClick }: { hidden: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      className="scroll-to-latest"
      hidden={hidden}
      aria-label="Scroll to latest message"
      onClick={onClick}
    >
      ↓ New messages
    </button>
  );
}
