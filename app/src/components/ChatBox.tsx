import type { ChatEntry } from "../types";
import { useAutoScroll } from "../hooks/useAutoScroll";
import { UserBubble } from "./UserBubble";
import { BotBubble } from "./BotBubble";
import { SuggestionChips } from "./SuggestionChips";
import { ScrollToLatestButton } from "./ScrollToLatestButton";
import { useI18n } from "../i18n";
import { shouldOfferHandoff } from "../lib/handoff";

export function ChatBox({
  entries,
  chipsHidden,
  onSelectSuggestion,
  onRegenerate,
  onRetry,
  onFeedback,
  helpUrl = null,
}: {
  entries: ChatEntry[];
  chipsHidden: boolean;
  onSelectSuggestion: (prompt: string) => void;
  onRegenerate: (id: string) => void;
  onRetry: (id: string) => void;
  // Set only when the library collects feedback (Tier 8 Phase 34).
  onFeedback?: (id: string) => Promise<boolean>;
  // Where "Talk to a librarian" goes, for the staff handoff.
  helpUrl?: string | null;
}) {
  const { t } = useI18n();
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
        <div className="bot intro">{t.intro}</div>
        <SuggestionChips hidden={chipsHidden} onSelect={onSelectSuggestion} />
        {entries.map((entry) =>
          entry.kind === "user" ? (
            <UserBubble key={entry.id} text={entry.text} />
          ) : (
            <BotBubble
              key={entry.id}
              entry={entry}
              onRegenerate={onRegenerate}
              onRetry={onRetry}
              onFeedback={onFeedback}
            />
          ),
        )}
        {shouldOfferHandoff(entries) && (
          <div className="staff-handoff" role="status">
            <p>{t.handoff}</p>
            {helpUrl ? (
              <a href={helpUrl} target="_blank" rel="noopener noreferrer">
                {t.talkToLibrarian}
              </a>
            ) : (
              <p>{t.handoffNoLink}</p>
            )}
          </div>
        )}
      </main>
      <ScrollToLatestButton hidden={!showScrollButton} onClick={scrollToBottom} />
    </>
  );
}
