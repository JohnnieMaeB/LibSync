import { useEffect, useRef } from "react";

// A plain-language account of what happens to a patron's messages, kept in
// step with how the backend actually behaves (see ARCHITECTURE.md and
// TIER8_PLAN.md §2.8). If any of these facts change in code, change them
// here in the same PR.
export function PrivacyDialog({ helpUrl, onClose }: { helpUrl: string | null; onClose: () => void }) {
  const headingRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null;
    headingRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
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
            <strong>Lookups:</strong> when you ask about a book, paper or citation, only the search terms are sent to
            Open Library, OpenAlex or Crossref.
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
