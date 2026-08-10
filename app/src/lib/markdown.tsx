import type { ReactNode } from "react";

// Escape-by-default inline renderer for a small markdown subset (**bold**,
// *italic*, [text](url) links). Everything else is emitted as plain text —
// this never touches dangerouslySetInnerHTML, so there is no code path where
// a string derived from (untrusted, possibly prompt-injected) model output
// can become live markup.
const INLINE_MARKDOWN_PATTERN = /\*\*(.+?)\*\*|\*(.+?)\*|\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g;

export function renderInlineMarkdownNodes(text: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let key = 0;
  INLINE_MARKDOWN_PATTERN.lastIndex = 0;
  while ((match = INLINE_MARKDOWN_PATTERN.exec(text)) !== null) {
    if (match.index > lastIndex) {
      nodes.push(text.slice(lastIndex, match.index));
    }
    if (match[1] !== undefined) {
      nodes.push(<strong key={key++}>{match[1]}</strong>);
    } else if (match[2] !== undefined) {
      nodes.push(<em key={key++}>{match[2]}</em>);
    } else if (match[3] !== undefined) {
      nodes.push(
        <a key={key++} href={match[4]} target="_blank" rel="noopener noreferrer">
          {match[3]}
        </a>,
      );
    }
    lastIndex = INLINE_MARKDOWN_PATTERN.lastIndex;
  }
  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex));
  }
  return nodes;
}

export function SafeMarkdown({ text }: { text: string }) {
  return <div className="bot-text">{renderInlineMarkdownNodes(text)}</div>;
}

// Fallback pattern for the (rare, non-streaming) case a plain-text reply
// still contains prose-formatted book lines, e.g.:
// - "Project Hail Mary" by Andy Weir (2021) — availability: lendable
const BOOK_LINE_PATTERN = /^-\s*"(.+)"\s*by\s*(.+?)(?:\s*\((\d{4})\))?\s*—\s*availability:\s*(.+)$/;

export interface ParsedBookLine {
  title: string;
  author: string;
  year?: string;
  availability: string;
}

// Returns parsed book lines only if every non-empty line in `text` matches
// the pattern; otherwise null (caller should fall back to renderInlineMarkdownNodes).
export function parseAllBookLines(text: string): ParsedBookLine[] | null {
  const nonEmptyLines = text.split("\n").filter((line) => line.trim());
  if (nonEmptyLines.length === 0) return null;
  const matches = nonEmptyLines.map((line) => line.match(BOOK_LINE_PATTERN));
  if (!matches.every((m): m is RegExpMatchArray => Boolean(m))) return null;
  return matches.map((m) => ({ title: m![1], author: m![2], year: m![3], availability: m![4] }));
}
