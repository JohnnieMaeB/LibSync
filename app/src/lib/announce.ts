// What a screen reader hears for a reply (WCAG 4.1.3, Status Messages).
// Streaming text must not be the live region itself: screen readers either
// queue every fragment and fall behind, or interrupt themselves and never read
// a whole answer. ChatBox therefore turns the conversation's own live
// announcements off and speaks through one status element instead: "answering",
// each search as it starts, then the finished reply once, as plain sentences.

import type { Messages } from "../i18n/messages";
import type { Block, BotEntry, ChatEntry } from "../types";

// Markdown and emoji read badly aloud ("asterisk asterisk", "books emoji").
function speakable(text: string): string {
  return text
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/[*_`#>|]+/g, "")
    .replace(/[☀-➿\u{1f000}-\u{1faff}️‍]/gu, "")
    .replace(/\s+/g, " ")
    .trim();
}

function blockText(block: Block, t: Messages): string {
  switch (block.type) {
    case "text":
      return speakable(block.text);
    case "book": {
      const { title, author, year, availability } = block.data;
      const status = t.availability[availability.trim()] ?? availability;
      return `${title}${year ? ` (${year})` : ""}, ${t.byAuthor(author)}, ${status}.`;
    }
    case "research":
      return [speakable(block.intro ?? ""), ...block.works.map(({ data }) => `${data.title}, ${data.authors}.`)]
        .filter(Boolean)
        .join(" ");
    case "citation":
      return block.data.formatted;
    case "account": {
      const { items } = block.data;
      return `${t.checkedOut}: ${items.charged?.length ?? 0}. ${t.overdue}: ${items.overdue?.length ?? 0}. ${t.onHold}: ${items.holds?.length ?? 0}.`;
    }
    default:
      return "";
  }
}

export function replyAnnouncement(entry: BotEntry, t: Messages): string {
  switch (entry.status) {
    case "loading":
      return t.announceAnswering;
    case "streaming":
      return ""; // nothing new to say until the reply is complete
    case "tool":
      return speakable(entry.toolLabel || t.working);
    case "error":
      return speakable(entry.errorText || t.somethingWrong);
    case "stopped":
      return t.stopped;
    case "done": {
      const body = entry.blocks.map((block) => blockText(block, t)).filter(Boolean).join(" ");
      return `${t.announceReplied} ${body || t.fallbackAnswer}`;
    }
    default:
      return "";
  }
}

// The newest reply, unless it was already there when the conversation opened
// (switching to an old conversation shouldn't read its last answer aloud).
export function latestNewReply(entries: ChatEntry[], seenAtOpen: Set<string>): BotEntry | null {
  for (let i = entries.length - 1; i >= 0; i -= 1) {
    const entry = entries[i];
    if (entry.kind === "bot") return seenAtOpen.has(entry.id) ? null : entry;
  }
  return null;
}
