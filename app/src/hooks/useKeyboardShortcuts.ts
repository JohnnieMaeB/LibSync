import { useEffect } from "react";

// Cmd/Ctrl+K for a new chat and Esc to close the mobile drawer match the
// convention shared by ChatGPT, Claude, and Linear (see TIER5_PLAN.md §3).
export function useKeyboardShortcuts({
  onNewChat,
  onEscape,
}: {
  onNewChat: () => void;
  onEscape: () => void;
}) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        onNewChat();
      } else if (e.key === "Escape") {
        onEscape();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onNewChat, onEscape]);
}
