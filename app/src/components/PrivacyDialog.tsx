import { useEffect, useRef } from "react";
import { useI18n } from "../i18n";

// A plain-language account of what happens to a patron's messages, kept in
// step with how the backend actually behaves (see ARCHITECTURE.md and
// TIER8_PLAN.md §2.8). The text lives in i18n/messages.ts (privacyItems); if
// any of these facts change in code, change them there, in every language, in
// the same PR.
export function PrivacyDialog({ helpUrl, onClose }: { helpUrl: string | null; onClose: () => void }) {
  const { t } = useI18n();
  const headingRef = useRef<HTMLHeadingElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null;
    headingRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
        return;
      }
      // Keep Tab inside the modal (aria-modal="true" promises that the page
      // behind it is inert to assistive technology; focus has to agree).
      if (event.key !== "Tab" || !dialogRef.current) return;
      const focusable = Array.from(
        dialogRef.current.querySelectorAll<HTMLElement>("a[href], button:not([disabled])"),
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement;
      const inside = dialogRef.current.contains(active);
      if (event.shiftKey && (active === first || !inside || active === headingRef.current)) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && (active === last || !inside)) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      opener?.focus();
    };
  }, [onClose]);

  return (
    <div className="privacy-overlay" onClick={onClose}>
      <div
        className="privacy-dialog"
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="privacy-title"
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id="privacy-title" tabIndex={-1} ref={headingRef}>
          {t.dataHandling}
        </h2>
        <ul>
          {t.privacyItems.map(([lead, rest]) => (
            <li key={lead}>
              <strong>{lead}</strong> {rest}
            </li>
          ))}
        </ul>
        <p>
          {t.privacyQuestions}{" "}
          {helpUrl ? (
            <a href={helpUrl} target="_blank" rel="noopener noreferrer">
              {t.talkToLibrarian}
            </a>
          ) : (
            t.askStaff
          )}
        </p>
        <button type="button" className="privacy-close" onClick={onClose}>
          {t.close}
        </button>
      </div>
    </div>
  );
}
