import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AiNotice } from "./AiNotice";

describe("AiNotice (Phase 36T)", () => {
  it("always discloses that the patron is talking to AI", () => {
    render(<AiNotice helpUrl={null} />);
    expect(screen.getByText(/chatting with an AI assistant/i)).toBeInTheDocument();
  });

  it("hides the librarian link when the library set none", () => {
    render(<AiNotice helpUrl={null} />);
    expect(screen.queryByRole("link", { name: "Talk to a librarian" })).toBeNull();
  });

  it("opens an accessible privacy dialog that Escape closes, returning focus", async () => {
    const user = userEvent.setup();
    render(<AiNotice helpUrl="https://lib.example/ask" />);
    const opener = screen.getByRole("button", { name: "How your data is handled" });

    await user.click(opener);
    const dialog = screen.getByRole("dialog", { name: "How your data is handled" });
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(screen.getByRole("heading", { name: "How your data is handled" })).toHaveFocus();
    expect(dialog).toHaveTextContent(/does not use your messages to train/i);

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(opener).toHaveFocus();
  });
});
