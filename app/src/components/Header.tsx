import logo from "../assets/logo.png";

// onClose is only passed in widget mode (see App.tsx's WidgetApp) — the
// standalone app has no host page to hand control back to.
export function Header({ onClose }: { onClose?: () => void } = {}) {
  return (
    <header>
      <img src={logo} alt="AI Assistant Logo" className="logo" />
      <div>
        <h1>LibSync</h1>
        <p className="tagline">Your personal AI library assistant.</p>
      </div>
      {onClose && (
        <button type="button" className="widget-close-btn" aria-label="Close chat" onClick={onClose}>
          ×
        </button>
      )}
    </header>
  );
}
