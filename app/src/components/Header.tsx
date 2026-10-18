import logo from "../assets/logo.png";
import { LanguagePicker, useI18n } from "../i18n";

// onClose is only passed in widget mode (see App.tsx's WidgetApp) — the
// standalone app has no host page to hand control back to.
export function Header({ onClose }: { onClose?: () => void } = {}) {
  const { t } = useI18n();
  return (
    <header>
      <img src={logo} alt={t.logoAlt} className="logo" />
      <div>
        <h1>LibSync</h1>
        <p className="tagline">{t.tagline}</p>
      </div>
      <LanguagePicker />
      {onClose && (
        <button type="button" className="widget-close-btn" aria-label={t.closeChat} onClick={onClose}>
          ×
        </button>
      )}
    </header>
  );
}
