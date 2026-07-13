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

  return (
    <footer>
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
        onClick={() => (isStreaming ? onStop() : submit())}
      >
        {isStreaming ? "Stop" : "Send"}
      </button>
    </footer>
  );
}
