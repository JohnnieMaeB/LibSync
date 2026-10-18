import type { BotEntry } from "../types";
import { SafeMarkdown } from "../lib/markdown";
import { blocksToPlainText } from "../lib/plainText";
import { BookCard } from "./BookCard";
import { ResearchResult } from "./ResearchResult";
import { CitationCard } from "./CitationCard";
import { MessageActions } from "./MessageActions";
import { AccountCard } from "./AccountCard";
import { useI18n } from "../i18n";

export function BotBubble({
  entry,
  onRegenerate,
  onRetry,
  onFeedback,
}: {
  entry: BotEntry;
  onRegenerate: (id: string) => void;
  onRetry: (id: string) => void;
  onFeedback?: (id: string) => Promise<boolean>;
}) {
  const { t } = useI18n();
  const isLoadingLike = entry.status === "loading" || entry.status === "tool";
  const className = ["bot", isLoadingLike ? "loading" : "", entry.status === "error" ? "error" : ""]
    .filter(Boolean)
    .join(" ");

  if (entry.status === "error") {
    return (
      <div className={className}>
        <SafeMarkdown text={entry.errorText || t.somethingWrong} />
        <button type="button" className="bot-retry" onClick={() => onRetry(entry.id)}>
          {t.retry}
        </button>
      </div>
    );
  }

  if (entry.status === "loading") {
    return <div className={className}>{t.thinking}</div>;
  }

  if (entry.status === "tool") {
    return (
      <div className={className}>
        <span className="tool-status-pill">{entry.toolLabel || t.working}</span>
      </div>
    );
  }

  const showFallback = entry.blocks.length === 0 && (entry.status === "done" || entry.status === "stopped");
  const finalized = entry.status === "done" || entry.status === "stopped";

  return (
    <div className={className}>
      {finalized && entry.cardCount > 0 && (
        <div className="grounded-tag">
          {t.grounded(entry.cardCount)}
        </div>
      )}
      {showFallback && <SafeMarkdown text={entry.status === "stopped" ? t.stopped : t.fallbackAnswer} />}
      {entry.blocks.map((block) => {
        switch (block.type) {
          case "text":
            return <SafeMarkdown key={block.key} text={block.text} />;
          case "book":
            return <BookCard key={block.key} data={block.data} number={block.number} />;
          case "research":
            return <ResearchResult key={block.key} intro={block.intro} works={block.works} />;
          case "citation":
            return <CitationCard key={block.key} data={block.data} number={block.number} />;
          case "account":
            return <AccountCard key={block.key} data={block.data} />;
          default:
            return null;
        }
      })}
      {entry.status === "stopped" && entry.blocks.length > 0 && (
        <div className="bot-text">{t.stoppedTag}</div>
      )}
      {finalized && (
        <MessageActions
          text={blocksToPlainText(entry.blocks)}
          onRegenerate={entry.isLatest ? () => onRegenerate(entry.id) : undefined}
          onFeedback={onFeedback ? () => onFeedback(entry.id) : undefined}
        />
      )}
    </div>
  );
}
