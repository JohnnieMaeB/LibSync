import { useEffect, useRef, useState } from "react";
import type { ChatEntry } from "../types";

const NEAR_BOTTOM_THRESHOLD = 60;

// Streaming growth mustn't yank a scrolled-up reader back to the bottom —
// only auto-follow if they were already near it, otherwise surface the
// floating "scroll to latest" escape hatch. A brand-new entry (a fresh user
// message or bot placeholder), by contrast, always snaps to the bottom.
export function useAutoScroll(entries: ChatEntry[]) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const prevLengthRef = useRef(entries.length);

  const isNearBottom = () => {
    const el = containerRef.current;
    if (!el) return true;
    return el.scrollHeight - el.scrollTop - el.clientHeight < NEAR_BOTTOM_THRESHOLD;
  };

  const scrollToBottom = () => {
    const el = containerRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
    setShowScrollButton(false);
  };

  useEffect(() => {
    const isNewEntry = entries.length !== prevLengthRef.current;
    prevLengthRef.current = entries.length;
    if (isNewEntry) {
      scrollToBottom();
    } else if (isNearBottom()) {
      scrollToBottom();
    } else {
      setShowScrollButton(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entries]);

  const handleScroll = () => {
    setShowScrollButton(!isNearBottom());
  };

  return { containerRef, showScrollButton, scrollToBottom, handleScroll };
}
