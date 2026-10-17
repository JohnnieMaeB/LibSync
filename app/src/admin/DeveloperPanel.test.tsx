import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DeveloperPanel } from "./DeveloperPanel";
import type { LibraryRow } from "./AdminApp";

const LIBRARY: LibraryRow = {
  id: "springfield-pl",
  name: "S",
  help_url: null,
  enabled_tools: null,
  ai_enabled: true,
  allowed_origins: null,
  feedback_webhook: null,
};

function json(body: unknown, ok = true) {
  return { ok, json: async () => body };
}

function supabase() {
  const eq = vi.fn(async () => ({ error: null }));
  const update = vi.fn(() => ({ eq }));
  return { client: { from: vi.fn(() => ({ update })) } as never, update };
}

describe("DeveloperPanel (Tier 8 Phase 34)", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("creates a key and shows it once", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(json([]))
        .mockResolvedValueOnce(json({ id: "k1", name: "ILS", prefix: "ls_abc1234", key: "ls_secretvalue" }))
        .mockResolvedValueOnce(json([{ id: "k1", name: "ILS", prefix: "ls_abc1234", created_at: "", revoked_at: null }])),
    );
    const user = userEvent.setup();
    render(<DeveloperPanel {...supabase()} library={LIBRARY} accessToken="t" />);
    await user.type(screen.getByLabelText("New key name"), "ILS");
    await user.click(screen.getByRole("button", { name: "Create key (admins)" }));
    expect(await screen.findByText("ls_secretvalue")).toBeInTheDocument();
    expect(screen.getByText(/won't be shown again/)).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Revoke ILS" })).toBeInTheDocument();
  });

  it("rejects a non-https webhook and saves an https one", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => json([])));
    const { client, update } = supabase();
    const user = userEvent.setup();
    render(<DeveloperPanel client={client} library={LIBRARY} accessToken="t" />);
    const field = screen.getByLabelText(/Feedback webhook/);
    await user.type(field, "http://insecure.example");
    await user.click(screen.getByRole("button", { name: "Save webhook" }));
    expect(update).not.toHaveBeenCalled();
    await user.clear(field);
    await user.type(field, "https://hooks.example/x");
    await user.click(screen.getByRole("button", { name: "Save webhook" }));
    expect(update).toHaveBeenCalledWith({ feedback_webhook: "https://hooks.example/x" });
  });
});
