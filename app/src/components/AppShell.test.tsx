import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AppShell } from "./AppShell";

const noop = () => {};

describe("AppShell", () => {
  it("keeps the mobile drawer closed by default and opens it via the sidebar toggle", async () => {
    const user = userEvent.setup();
    render(
      <AppShell
        conversations={[]}
        activeId={null}
        onNewChat={noop}
        onSelectConversation={noop}
        onRenameConversation={noop}
        onDeleteConversation={noop}
      >
        <div>content</div>
      </AppShell>,
    );

    const nav = screen.getByRole("navigation", { name: "Conversations" });
    expect(nav.className).not.toContain("open");

    await user.click(screen.getByRole("button", { name: "Open sidebar" }));
    expect(nav.className).toContain("open");
  });

  it("closes the drawer when the overlay is clicked", async () => {
    const user = userEvent.setup();
    render(
      <AppShell
        conversations={[]}
        activeId={null}
        onNewChat={noop}
        onSelectConversation={noop}
        onRenameConversation={noop}
        onDeleteConversation={noop}
      >
        <div>content</div>
      </AppShell>,
    );

    await user.click(screen.getByRole("button", { name: "Open sidebar" }));
    const nav = screen.getByRole("navigation", { name: "Conversations" });
    expect(nav.className).toContain("open");

    await user.click(document.querySelector(".sidebar-overlay")!);
    expect(nav.className).not.toContain("open");
  });

  it("closes the drawer on Escape", async () => {
    const user = userEvent.setup();
    render(
      <AppShell
        conversations={[]}
        activeId={null}
        onNewChat={noop}
        onSelectConversation={noop}
        onRenameConversation={noop}
        onDeleteConversation={noop}
      >
        <div>content</div>
      </AppShell>,
    );

    await user.click(screen.getByRole("button", { name: "Open sidebar" }));
    const nav = screen.getByRole("navigation", { name: "Conversations" });
    expect(nav.className).toContain("open");

    await user.keyboard("{Escape}");
    expect(nav.className).not.toContain("open");
  });

  it("calls onNewChat on Cmd/Ctrl+K", async () => {
    const onNewChat = vi.fn();
    render(
      <AppShell
        conversations={[]}
        activeId={null}
        onNewChat={onNewChat}
        onSelectConversation={noop}
        onRenameConversation={noop}
        onDeleteConversation={noop}
      >
        <div>content</div>
      </AppShell>,
    );

    await userEvent.setup().keyboard("{Control>}k{/Control}");
    expect(onNewChat).toHaveBeenCalledTimes(1);
  });

  it("renders children directly, without the sidebar, in compact mode", () => {
    render(
      <AppShell
        compact
        conversations={[]}
        activeId={null}
        onNewChat={noop}
        onSelectConversation={noop}
        onRenameConversation={noop}
        onDeleteConversation={noop}
      >
        <div>content</div>
      </AppShell>,
    );

    expect(screen.queryByRole("navigation", { name: "Conversations" })).toBeNull();
    expect(screen.getByText("content")).toBeInTheDocument();
  });

  it("toggles collapsed state via the collapse button", async () => {
    const user = userEvent.setup();
    render(
      <AppShell
        conversations={[]}
        activeId={null}
        onNewChat={noop}
        onSelectConversation={noop}
        onRenameConversation={noop}
        onDeleteConversation={noop}
      >
        <div>content</div>
      </AppShell>,
    );

    const nav = screen.getByRole("navigation", { name: "Conversations" });
    expect(nav.className).not.toContain("collapsed");

    await user.click(screen.getByRole("button", { name: "Collapse sidebar" }));
    expect(nav.className).toContain("collapsed");
    expect(screen.getByRole("button", { name: "Expand sidebar" })).toBeInTheDocument();
  });
});
