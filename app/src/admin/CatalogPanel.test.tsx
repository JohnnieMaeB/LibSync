import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CatalogPanel } from "./CatalogPanel";
import type { LibraryRow } from "./AdminApp";

const LIBRARY: LibraryRow = {
  id: "springfield-pl",
  name: "Springfield",
  help_url: null,
  enabled_tools: null,
  ai_enabled: true,
  allowed_origins: null,
  catalog_driver: "openlibrary",
  catalog_config: {},
};

function mockClient() {
  const eq = vi.fn(async () => ({ error: null }));
  const update = vi.fn(() => ({ eq }));
  const upsert = vi.fn(async () => ({ error: null }));
  const from = vi.fn((table: string) => (table === "library_secrets" ? { upsert } : { update }));
  return { client: { from } as never, update, upsert, eq };
}

describe("CatalogPanel (Tier 8 Phase 32)", () => {
  it("saves a Koha driver's settings and writes its secret separately", async () => {
    const { client, update, upsert } = mockClient();
    const user = userEvent.setup();
    render(<CatalogPanel client={client} library={LIBRARY} />);

    await user.selectOptions(screen.getByLabelText("Search this catalog"), "koha");
    await user.type(screen.getByLabelText("Koha staff interface URL"), "https://staff.koha.example");
    await user.type(screen.getByLabelText("API client ID"), "cid");
    await user.type(screen.getByLabelText(/API client secret/), "s3cret");
    await user.click(screen.getByRole("button", { name: "Save catalog" }));

    expect(update).toHaveBeenCalledWith({
      catalog_driver: "koha",
      catalog_config: { base_url: "https://staff.koha.example", client_id: "cid" },
    });
    expect(upsert).toHaveBeenCalledWith({ library_id: "springfield-pl", name: "koha_client_secret", value: "s3cret" });
    expect(await screen.findByText(/falls back to Open Library/)).toBeInTheDocument();
    expect(screen.getByLabelText(/API client secret/)).toHaveValue("");
  });

  it("keeps the stored secret when the field is left blank", async () => {
    const { client, upsert } = mockClient();
    const user = userEvent.setup();
    render(<CatalogPanel client={client} library={{ ...LIBRARY, catalog_driver: "polaris" }} />);
    await user.click(screen.getByRole("button", { name: "Save catalog" }));
    expect(upsert).not.toHaveBeenCalled();
  });

  it("the secret field is a password input", () => {
    const { client } = mockClient();
    render(<CatalogPanel client={client} library={{ ...LIBRARY, catalog_driver: "koha" }} />);
    expect(screen.getByLabelText(/API client secret/)).toHaveAttribute("type", "password");
  });
});
