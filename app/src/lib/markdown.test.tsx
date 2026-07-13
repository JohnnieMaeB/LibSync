import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { SafeMarkdown, parseAllBookLines } from "./markdown";

describe("SafeMarkdown", () => {
  it("renders bold, italic, and links as real elements", () => {
    render(<SafeMarkdown text="**bold** *italic* [LibSync](https://example.com/libsync)" />);
    expect(screen.getByText("bold").tagName).toBe("STRONG");
    expect(screen.getByText("italic").tagName).toBe("EM");
    const link = screen.getByRole("link", { name: "LibSync" });
    expect(link).toHaveAttribute("href", "https://example.com/libsync");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("never renders raw HTML/script tags as live markup", () => {
    const { container } = render(
      <SafeMarkdown text={'<img src=x onerror="alert(1)"> <script>alert(2)</script>'} />,
    );
    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("script")).toBeNull();
    expect(container.textContent).toContain("<img src=x onerror=\"alert(1)\">");
    expect(container.textContent).toContain("<script>alert(2)</script>");
  });
});

describe("parseAllBookLines", () => {
  it("parses a plain-text book line", () => {
    const parsed = parseAllBookLines('- "Project Hail Mary" by Andy Weir (2021) — availability: lendable');
    expect(parsed).toEqual([
      { title: "Project Hail Mary", author: "Andy Weir", year: "2021", availability: "lendable" },
    ]);
  });

  it("returns null when any line doesn't match", () => {
    expect(parseAllBookLines("Thinking...")).toBeNull();
  });
});
