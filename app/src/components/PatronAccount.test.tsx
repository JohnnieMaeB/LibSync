import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PatronAccount } from "./PatronAccount";
import { consumeMagicLink, loadSession } from "../patron";
import { standaloneLibraryId } from "../widget";

const SESSION_BODY = { token: "opaque", kind: "card", library_id: "springfield-pl", expires_at: 4102444800 };

describe("PatronAccount (Tier 9 Phase 36)", () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => vi.unstubAllGlobals());

  it("renders nothing when the library offers no accounts", () => {
    const { container } = render(
      <PatronAccount libraryId="springfield-pl" methods={[]} session={null} onSessionChange={() => {}} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("offers card sign-in as optional and signs in", async () => {
    const fetchMock = vi.fn(async () => ({ ok: true, json: async () => SESSION_BODY }));
    vi.stubGlobal("fetch", fetchMock);
    const onSessionChange = vi.fn();
    const user = userEvent.setup();
    render(<PatronAccount libraryId="springfield-pl" methods={["card"]} session={null} onSessionChange={onSessionChange} />);

    expect(screen.getByText(/keep chatting without an account/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Sign in with your library card" }));
    await user.type(screen.getByLabelText("Library card number"), "21234000567890");
    await user.type(screen.getByLabelText("PIN"), "4321");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(onSessionChange).toHaveBeenCalledWith(expect.objectContaining({ token: "opaque", kind: "card" }));
    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(JSON.parse(String(init.body))).toEqual({ card: "21234000567890", pin: "4321" });
    expect(localStorage.getItem("libsync:patron")).not.toContain("4321"); // the PIN is never kept
    expect(screen.getByLabelText("PIN")).toHaveValue("");
  });

  it("shows the library's reason when sign-in fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: false, json: async () => ({ detail: "That card number and PIN weren't recognized." }) })),
    );
    const user = userEvent.setup();
    render(<PatronAccount libraryId="springfield-pl" methods={["card"]} session={null} onSessionChange={() => {}} />);
    await user.click(screen.getByRole("button", { name: "Sign in with your library card" }));
    await user.type(screen.getByLabelText("Library card number"), "1");
    await user.type(screen.getByLabelText("PIN"), "2");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByText(/weren't recognized/)).toBeInTheDocument();
  });

  it("signs out", async () => {
    localStorage.setItem("libsync:patron", JSON.stringify({ ...SESSION_BODY, libraryId: "springfield-pl", expiresAt: 4102444800 }));
    const onSessionChange = vi.fn();
    const user = userEvent.setup();
    render(
      <PatronAccount
        libraryId="springfield-pl"
        methods={["card"]}
        session={{ token: "t", kind: "card", libraryId: "springfield-pl", expiresAt: 4102444800 }}
        onSessionChange={onSessionChange}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Sign out" }));
    expect(onSessionChange).toHaveBeenCalledWith(null);
    expect(localStorage.getItem("libsync:patron")).toBeNull();
  });
});

describe("patron session helpers", () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => {
    vi.unstubAllGlobals();
    window.history.pushState({}, "", "/");
  });

  it("ignores expired sessions and other libraries' sessions", () => {
    localStorage.setItem("libsync:patron", JSON.stringify({ token: "t", kind: "card", libraryId: "a", expiresAt: 1 }));
    expect(loadSession("a")).toBeNull();
    localStorage.setItem("libsync:patron", JSON.stringify({ token: "t", kind: "card", libraryId: "a", expiresAt: 4102444800 }));
    expect(loadSession("b")).toBeNull();
    expect(loadSession("a")?.token).toBe("t");
  });

  it("exchanges a magic link and removes it from the address bar", async () => {
    window.history.pushState({}, "", "/?library=springfield-pl#access_token=supa&type=magiclink");
    const fetchMock = vi.fn(async () => ({ ok: true, json: async () => ({ ...SESSION_BODY, kind: "email" }) }));
    vi.stubGlobal("fetch", fetchMock);
    const session = await consumeMagicLink("springfield-pl");
    expect(session?.kind).toBe("email");
    expect(window.location.hash).toBe("");
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toContain("/patron/sign-in/email");
    expect(JSON.parse(String(init.body))).toEqual({ access_token: "supa" });
  });

  it("remembers the standalone app's library and rejects malformed ids", () => {
    expect(standaloneLibraryId("?library=Springfield-PL")).toBe("springfield-pl");
    expect(standaloneLibraryId("")).toBe("springfield-pl");
    localStorage.clear();
    expect(standaloneLibraryId("?library=../x")).toBeNull();
  });
});
