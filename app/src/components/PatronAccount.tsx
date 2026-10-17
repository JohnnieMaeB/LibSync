import { useState, type FormEvent } from "react";
import { requestEmailLink, signInWithCard, signOut, type PatronSession } from "../patron";

// Tier 9 Phase 36: signing in is offered, never required (TIER9_PLAN.md §2).
// Card + PIN is checked by the library's own system; LibSync never keeps the PIN.

export function PatronAccount({
  libraryId,
  methods,
  session,
  onSessionChange,
}: {
  libraryId: string;
  methods: string[];
  session: PatronSession | null;
  onSessionChange: (session: PatronSession | null) => void;
}) {
  const [open, setOpen] = useState(false);
  const [card, setCard] = useState("");
  const [pin, setPin] = useState("");
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);

  if (session) {
    return (
      <div className="patron-account">
        <p>Signed in {session.kind === "card" ? "with your library card" : "by email"}.</p>
        <button
          type="button"
          className="patron-link"
          onClick={() => {
            signOut();
            onSessionChange(null);
          }}
        >
          Sign out
        </button>
      </div>
    );
  }

  if (methods.length === 0) return null;

  if (!open) {
    return (
      <div className="patron-account">
        <button type="button" className="patron-link" onClick={() => setOpen(true)}>
          {methods.includes("card") ? "Sign in with your library card" : "Sign in"}
        </button>
        <p className="patron-hint">Optional. You can keep chatting without an account.</p>
      </div>
    );
  }

  async function cardSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setStatus("");
    try {
      onSessionChange(await signInWithCard(libraryId, card.trim(), pin));
      setPin("");
    } catch (error) {
      setStatus((error as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function emailSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await requestEmailLink(libraryId, email.trim());
      setStatus("Check your email for a sign-in link.");
    } catch (error) {
      setStatus((error as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="patron-account" aria-label="Sign in">
      {methods.includes("card") && (
        <form onSubmit={cardSubmit}>
          <label htmlFor="patron-card">Library card number</label>
          <input
            id="patron-card"
            inputMode="numeric"
            autoComplete="username"
            required
            value={card}
            onChange={(e) => setCard(e.target.value)}
          />
          <label htmlFor="patron-pin">PIN</label>
          <input
            id="patron-pin"
            type="password"
            autoComplete="current-password"
            required
            value={pin}
            onChange={(e) => setPin(e.target.value)}
          />
          <button type="submit" disabled={busy}>
            Sign in
          </button>
        </form>
      )}
      {methods.includes("email") && (
        <form onSubmit={emailSubmit}>
          <label htmlFor="patron-email">{methods.includes("card") ? "Or use your email" : "Email"}</label>
          <input
            id="patron-email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <button type="submit" disabled={busy}>
            Email me a sign-in link
          </button>
        </form>
      )}
      <p role="status">{status}</p>
      <button type="button" className="patron-link" onClick={() => setOpen(false)}>
        Continue without an account
      </button>
    </section>
  );
}
