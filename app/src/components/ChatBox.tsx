import { useState } from "react";
import type { ChatEntry } from "../types";
import { useAutoScroll } from "../hooks/useAutoScroll";
import { UserBubble } from "./UserBubble";
import { BotBubble } from "./BotBubble";
import { SuggestionChips } from "./SuggestionChips";
import { ScrollToLatestButton } from "./ScrollToLatestButton";
import { useI18n } from "../i18n";
import { shouldOfferHandoff } from "../lib/handoff";
import { latestNewReply, replyAnnouncement } from "../lib/announce";

export function ChatBox({
  entries,
  chipsHidden,
  onSelectSuggestion,
  onRegenerate,
  onRetry,
  onFeedback,
  helpUrl = null,
  teachSearch = false,
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
  // The library's "teach the search" setting: search steps open by default.
  teachSearch?: boolean;
}) {
  const { t } = useI18n();
  const { containerRef, showScrollButton, scrollToBottom, handleScroll } = useAutoScroll(entries);
  // Replies already here when this conversation opened aren't read aloud again.
  const [seenAtOpen] = useState(() => new Set(entries.filter((e) => e.kind === "bot").map((e) => e.id)));
  const reply = latestNewReply(entries, seenAtOpen);
  const announcement = reply ? replyAnnouncement(reply, t) : "";
  const busy = reply !== null && ["loading", "tool", "streaming"].includes(reply.status);

  return (
    <>
      <main
        id="chatBox"
        role="log"
        // Not a live region: streamed tokens would be read as fragments. The
        // status element below announces each reply once (lib/announce.ts).
        aria-live="off"
        aria-busy={busy}
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
              teachSearch={teachSearch}
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
      <div className="visually-hidden" role="status" aria-live="polite" aria-atomic="true">
        {announcement}
      </div>
      <ScrollToLatestButton hidden={!showScrollButton} onClick={scrollToBottom} />
    </>
  );
}
