import { useEffect, useRef } from "react";

// A plain-language account of what happens to a patron's messages, kept in
// step with how the backend actually behaves (see ARCHITECTURE.md and
// TIER8_PLAN.md §2.8). If any of these facts change in code, change them
// here in the same PR.
export function PrivacyDialog({ helpUrl, onClose }: { helpUrl: string | null; onClose: () => void }) {
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
          How your data is handled
        </h2>
        <ul>
          <li>
            <strong>This is an AI assistant.</strong> Your messages go to LibSync's server, which sends them to an AI
            provider (Groq, or Hugging Face if Groq is unavailable) to write a reply. LibSync does not use your
            messages to train AI models.
          </li>
          <li>
            <strong>What LibSync keeps:</strong> the server holds a conversation in memory for up to an hour so the
            assistant can follow along, then discards it. There is no chat database, and diagnostic logs record
            timing and errors, not what you wrote.
          </li>
          <li>
            <strong>On your device:</strong> the full LibSync app saves your conversations in this browser so you can
            come back to them. Delete any of them from the sidebar. The chat on a library's website saves nothing
            after you close the page.
          </li>
          <li>
            <strong>Lookups:</strong> to answer, the assistant may send search terms (not your whole conversation) to
            LibSync's library-policy index (Pinecone) or to Open Library, OpenAlex or Crossref for books, papers and
            citations.
          </li>
          <li>
            <strong>No accounts, ads or tracking cookies.</strong> Please don't share your library card number, PIN,
            passwords or other personal details in the chat.
          </li>
        </ul>
        <p>
          Questions, or need a person?{" "}
          {helpUrl ? (
            <a href={helpUrl} target="_blank" rel="noopener noreferrer">
              Talk to a librarian
            </a>
          ) : (
            "Ask library staff."
          )}
        </p>
        <button type="button" className="privacy-close" onClick={onClose}>
          Close
        </button>
      </div>
    </div>
  );
}
