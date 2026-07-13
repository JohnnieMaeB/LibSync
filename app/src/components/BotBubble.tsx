import type { BotEntry } from "../types";
import { SafeMarkdown } from "../lib/markdown";
import { blocksToPlainText } from "../lib/plainText";
import { BookCard } from "./BookCard";
import { ResearchResult } from "./ResearchResult";
import { CitationCard } from "./CitationCard";
import { MessageActions } from "./MessageActions";

const FALLBACK_TEXT = "Sorry, I couldn’t find an answer right now.";

export function BotBubble({
  entry,
  onRegenerate,
  onRetry,
}: {
  entry: BotEntry;
  onRegenerate: (id: string) => void;
  onRetry: (id: string) => void;
}) {
  const isLoadingLike = entry.status === "loading" || entry.status === "tool";
  const className = ["bot", isLoadingLike ? "loading" : "", entry.status === "error" ? "error" : ""]
    .filter(Boolean)
    .join(" ");

  if (entry.status === "error") {
    return (
      <div className={className}>
        <SafeMarkdown text={entry.errorText || "Something went wrong."} />
        <button type="button" className="bot-retry" onClick={() => onRetry(entry.id)}>
          Retry
        </button>
      </div>
    );
  }

  if (entry.status === "loading") {
    return <div className={className}>Thinking...</div>;
  }

  if (entry.status === "tool") {
    return (
      <div className={className}>
        <span className="tool-status-pill">{entry.toolLabel || "Working"}</span>
      </div>
    );
  }

  const showFallback = entry.blocks.length === 0 && (entry.status === "done" || entry.status === "stopped");
  const finalized = entry.status === "done" || entry.status === "stopped";

  return (
    <div className={className}>
      {finalized && entry.cardCount > 0 && (
        <div className="grounded-tag">
          Grounded in {entry.cardCount} source{entry.cardCount === 1 ? "" : "s"}
        </div>
      )}
      {showFallback && <SafeMarkdown text={entry.status === "stopped" ? "Stopped." : FALLBACK_TEXT} />}
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
          default:
            return null;
        }
      })}
      {entry.status === "stopped" && entry.blocks.length > 0 && (
        <div className="bot-text">(Stopped)</div>
      )}
      {finalized && (
        <MessageActions
          text={blocksToPlainText(entry.blocks)}
          onRegenerate={entry.isLatest ? () => onRegenerate(entry.id) : undefined}
        />
      )}
    </div>
  );
}
