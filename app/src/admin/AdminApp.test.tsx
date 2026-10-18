import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AdminApp, { parseOrigins, type LibraryRow } from "./AdminApp";

const LIBRARY: LibraryRow = {
  id: "springfield-pl",
  name: "Springfield Public Library",
  help_url: null,
  enabled_tools: null,
  ai_enabled: true,
  allowed_origins: null,
};

function mockClient({ session = null as unknown, libraries = [LIBRARY] } = {}) {
  const update = vi.fn(() => ({ eq: vi.fn(async () => ({ error: null })) }));
  const client = {
    auth: {
      getSession: vi.fn(async () => ({ data: { session } })),
      onAuthStateChange: vi.fn(() => ({ data: { subscription: { unsubscribe: vi.fn() } } })),
      signInWithOtp: vi.fn(async () => ({ error: null })),
      signInWithOAuth: vi.fn(async () => ({ error: null })),
      signOut: vi.fn(async () => ({ error: null })),
    },
    from: vi.fn(() => ({
      select: vi.fn(() => Promise.resolve({ data: libraries, error: null })),
      update,
    })),
  };
  return { client, update };
}

const SESSION = { access_token: "token-1", user: { email: "staff@springfield.example" } };

describe("staff dashboard (Tier 8 Phase 30)", () => {
  beforeEach(() => {
    // The documents panel (Phase 31) loads its list on mount.
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, status: 200, json: async () => [] })));
  });
  afterEach(() => vi.unstubAllGlobals());

  it("says it isn't set up when Supabase isn't configured", () => {
    render(<AdminApp client={null} />);
    expect(screen.getByText(/isn't set up for this deployment/i)).toBeInTheDocument();
  });

  it("offers Microsoft, Google and invite-only email sign-in", async () => {
    const { client } = mockClient();
    const user = userEvent.setup();
    render(<AdminApp client={client as never} />);

    await user.click(await screen.findByRole("button", { name: "Sign in with Microsoft" }));
    expect(client.auth.signInWithOAuth).toHaveBeenCalledWith(expect.objectContaining({ provider: "azure" }));

    await user.type(screen.getByLabelText(/sign-in link by email/i), "staff@springfield.example");
    await user.click(screen.getByRole("button", { name: "Email me a link" }));
    expect(client.auth.signInWithOtp).toHaveBeenCalledWith(
      expect.objectContaining({ options: expect.objectContaining({ shouldCreateUser: false }) }),
    );
    expect(await screen.findByText(/check your email/i)).toBeInTheDocument();
  });

  it("lets staff switch the assistant off and limit tools", async () => {
    const { client, update } = mockClient({ session: SESSION });
    const user = userEvent.setup();
    render(<AdminApp client={client as never} />);

    await screen.findByRole("heading", { name: "Springfield Public Library" });
    await user.click(screen.getByLabelText("AI assistant is on"));
    await user.click(screen.getByLabelText("Research papers"));
    await user.type(screen.getByLabelText(/talk to a librarian/i), "tel:+15555550100");
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(update).toHaveBeenCalledWith({
      name: "Springfield Public Library",
      ai_enabled: false,
      help_url: "tel:+15555550100",
      enabled_tools: ["policies", "catalog", "recommendations", "citations", "ebooks", "rooms", "account"],
      allowed_origins: null,
    });
    expect(await screen.findByText(/saved/i)).toBeInTheDocument();
  });

  it("rejects an unsafe librarian link without saving", async () => {
    const { client, update } = mockClient({ session: SESSION });
    const user = userEvent.setup();
    render(<AdminApp client={client as never} />);
    await screen.findByRole("heading", { name: "Springfield Public Library" });
    await user.type(screen.getByLabelText(/talk to a librarian/i), "javascript:alert(1)");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(update).not.toHaveBeenCalled();
    expect(screen.getByText(/must start with https/i)).toBeInTheDocument();
  });

  it("explains when the account isn't linked to a library", async () => {
    const { client } = mockClient({ session: SESSION, libraries: [] });
    render(<AdminApp client={client as never} />);
    expect(await screen.findByText(/isn't linked to a library yet/i)).toBeInTheDocument();
  });
});

describe("parseOrigins", () => {
  it("accepts bare origins, one per line", () => {
    expect(parseOrigins("https://a.example\nhttps://b.example/")).toEqual({
      origins: ["https://a.example", "https://b.example"],
      invalid: [],
    });
  });

  it("treats an empty box as any origin", () => {
    expect(parseOrigins("  ")).toEqual({ origins: null, invalid: [] });
  });

  it("flags paths and non-URLs", () => {
    expect(parseOrigins("https://a.example/page library.example").invalid).toEqual([
      "https://a.example/page",
      "library.example",
    ]);
  });
});
