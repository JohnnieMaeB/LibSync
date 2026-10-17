import { describe, expect, it } from "vitest";
import { renderHook } from "@testing-library/react";
import { useAutoScroll } from "./useAutoScroll";
import type { ChatEntry } from "../types";

function attach(result: { current: ReturnType<typeof useAutoScroll> }, box: Partial<HTMLDivElement>) {
  (result.current.containerRef as { current: unknown }).current = { scrollTop: 0, ...box };
}

describe("useAutoScroll", () => {
  it("never shows the scroll-to-latest button on an empty chat", () => {
    const { result, rerender } = renderHook(({ entries }) => useAutoScroll(entries), {
      initialProps: { entries: [] as ChatEntry[] },
    });
    // A box that hasn't been laid out yet (0 tall) holding the intro text.
    attach(result, { clientHeight: 0, scrollHeight: 400 });
    rerender({ entries: [] });
    expect(result.current.showScrollButton).toBe(false);
  });

  it("still offers it when a reader has scrolled up during a streaming reply", () => {
    const entries: ChatEntry[] = [{ kind: "user", id: "u", text: "hi" }];
    const { result, rerender } = renderHook(({ e }) => useAutoScroll(e), { initialProps: { e: entries } });
    attach(result, { clientHeight: 300, scrollHeight: 2000, scrollTop: 100 });
    rerender({ e: [...entries] }); // same length: streaming growth, not a new entry
    expect(result.current.showScrollButton).toBe(true);
  });
});
