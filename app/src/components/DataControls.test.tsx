import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DeviceDataControls } from "./DataControls";
import { PatronAccount } from "./PatronAccount";

describe("privacy controls (Tier 9 Phase 39)", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("asks before deleting this device's conversations, and can be cancelled", async () => {
    const clear = vi.fn(async () => {});
    const user = userEvent.setup();
    render(<DeviceDataControls onClearDevice={clear} />);

    await user.click(screen.getByRole("button", { name: "Delete all conversations on this device" }));
    expect(screen.getByText(/can't be undone/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(clear).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Delete all conversations on this device" }));
    await user.click(screen.getByRole("button", { name: "Delete" }));
    expect(clear).toHaveBeenCalledOnce();
    expect(await screen.findByText("Deleted.")).toBeInTheDocument();
  });

  it("lets a signed-in patron see what's kept and delete their synced history", async () => {
    const fetchMock = vi.fn(async () => ({ ok: true, json: async () => ({ deleted: "all" }) }));
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(
      <PatronAccount
        libraryId="springfield-pl"
        methods={["card"]}
        session={{ token: "tok", kind: "card", libraryId: "springfield-pl", expiresAt: 4102444800 }}
        onSessionChange={() => {}}
      />,
    );
    await user.click(screen.getByText("Your data"));
    expect(screen.getByText(/deleted automatically after 90 days/)).toBeInTheDocument();
    expect(screen.getByText(/never stores your PIN/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Delete my synced history" }));
    await user.click(screen.getByRole("button", { name: "Delete" }));
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toContain("/patron/conversations");
    expect(init.method).toBe("DELETE");
    expect(await screen.findByText("Deleted.")).toBeInTheDocument();
  });

  it("reports a failed deletion instead of claiming success", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: false, json: async () => ({}) })));
    const user = userEvent.setup();
    render(
      <PatronAccount
        libraryId="springfield-pl"
        methods={["email"]}
        session={{ token: "tok", kind: "email", libraryId: "springfield-pl", expiresAt: 4102444800 }}
        onSessionChange={() => {}}
      />,
    );
    await user.click(screen.getByText("Your data"));
    expect(screen.queryByText(/PIN/)).toBeNull();
    await user.click(screen.getByRole("button", { name: "Delete my synced history" }));
    await user.click(screen.getByRole("button", { name: "Delete" }));
    expect(await screen.findByText(/Couldn't delete/)).toBeInTheDocument();
  });
});
