import { useRef, useState } from "react";
import type { KeyboardEvent } from "react";

export function Composer({
  isStreaming,
  onSend,
  onStop,
}: {
  isStreaming: boolean;
  onSend: (text: string) => void;
  onStop: () => void;
}) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const resize = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
  };

  const submit = () => {
    const question = value.trim();
    if (!question) return;
    setValue("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
    onSend(question);
  };

  // onKeyDown, not the deprecated onKeyPress: keypress is unreliable for
  // Enter across modern browsers and is being phased out of the DOM spec.
  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!isStreaming) submit();
    }
  };

  const canSend = isStreaming || value.trim().length > 0;

  return (
    <footer>
      <div className="composer-bar">
        <textarea
          ref={textareaRef}
          id="userInput"
          placeholder="Type your question here..."
          aria-label="Type your question"
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            resize();
          }}
          onKeyDown={handleKeyDown}
        />
        <button
          id="sendBtn"
          className={isStreaming ? "stopping" : ""}
          aria-label={isStreaming ? "Stop generating" : "Send message"}
          disabled={!canSend}
          onClick={() => (isStreaming ? onStop() : submit())}
        >
          {isStreaming ? (
            <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <rect x="6" y="6" width="12" height="12" rx="2" />
            </svg>
          ) : (
            <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path
                d="M12 19V5M12 5l-6 6M12 5l6 6"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          )}
        </button>
      </div>
    </footer>
  );
}
