import type { ChatEntry } from "../types";
import { useAutoScroll } from "../hooks/useAutoScroll";
import { UserBubble } from "./UserBubble";
import { BotBubble } from "./BotBubble";
import { SuggestionChips } from "./SuggestionChips";
import { ScrollToLatestButton } from "./ScrollToLatestButton";

export function ChatBox({
  entries,
  chipsHidden,
  onSelectSuggestion,
  onRegenerate,
  onRetry,
}: {
  entries: ChatEntry[];
  chipsHidden: boolean;
  onSelectSuggestion: (prompt: string) => void;
  onRegenerate: (id: string) => void;
  onRetry: (id: string) => void;
}) {
  const { containerRef, showScrollButton, scrollToBottom, handleScroll } = useAutoScroll(entries);

  return (
    <>
      <main
        id="chatBox"
        role="log"
        aria-live="polite"
        aria-relevant="additions"
        ref={containerRef}
        onScroll={handleScroll}
      >
        <div className="bot intro">👋 Hi! I’m your AI Library Assistant. How can I help you today?</div>
        <SuggestionChips hidden={chipsHidden} onSelect={onSelectSuggestion} />
        {entries.map((entry) =>
          entry.kind === "user" ? (
            <UserBubble key={entry.id} text={entry.text} />
          ) : (
            <BotBubble key={entry.id} entry={entry} onRegenerate={onRegenerate} onRetry={onRetry} />
          ),
        )}
      </main>
      <ScrollToLatestButton hidden={!showScrollButton} onClick={scrollToBottom} />
    </>
  );
}
