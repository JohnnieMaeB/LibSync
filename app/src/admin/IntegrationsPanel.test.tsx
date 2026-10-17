import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { IntegrationsPanel } from "./IntegrationsPanel";
import type { LibraryRow } from "./AdminApp";

function setup(integrations: LibraryRow["integrations"] = {}) {
  const eq = vi.fn(async () => ({ error: null }));
  const update = vi.fn(() => ({ eq }));
  const upsert = vi.fn(async () => ({ error: null }));
  const client = { from: vi.fn((table: string) => (table === "library_secrets" ? { upsert } : { update })) };
  const library: LibraryRow = {
    id: "springfield-pl",
    name: "Springfield",
    help_url: null,
    enabled_tools: null,
    ai_enabled: true,
    allowed_origins: null,
    integrations,
  };
  render(<IntegrationsPanel client={client as never} library={library} />);
  return { update, upsert };
}

describe("IntegrationsPanel (Tier 8 Phase 37T)", () => {
  it("connects OverDrive without touching LibCal, and writes the secret separately", async () => {
    const { update, upsert } = setup({ libcal: { site: "lib.libcal.com" } });
    const user = userEvent.setup();
    await user.type(screen.getByLabelText("OverDrive library ID"), "1234");
    await user.type(screen.getByLabelText("API client key"), "cid");
    await user.type(screen.getAllByLabelText(/API client secret/)[0], "sec");
    await user.click(screen.getByRole("button", { name: "Save OverDrive / Libby" }));

    expect(update).toHaveBeenCalledWith({
      integrations: { libcal: { site: "lib.libcal.com" }, overdrive: { library_id: "1234", client_id: "cid" } },
    });
    expect(upsert).toHaveBeenCalledWith({ library_id: "springfield-pl", name: "overdrive_client_secret", value: "sec" });
    expect(await screen.findByText("Connected.")).toBeInTheDocument();
  });

  it("disconnects a vendor when its fields are cleared", async () => {
    const { update } = setup({ libcal: { site: "lib.libcal.com" } });
    const user = userEvent.setup();
    await user.clear(screen.getByLabelText("LibCal site"));
    await user.click(screen.getByRole("button", { name: "Save Springshare LibCal" }));
    expect(update).toHaveBeenCalledWith({ integrations: {} });
    expect(await screen.findByText("Disconnected.")).toBeInTheDocument();
  });
});
