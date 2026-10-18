import { useState, type FormEvent } from "react";
import { deleteSyncedHistory, requestEmailLink, signInWithCard, signOut, type PatronSession } from "../patron";
import { ConfirmButton } from "./DataControls";
import { useI18n } from "../i18n";

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
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [card, setCard] = useState("");
  const [pin, setPin] = useState("");
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);

  if (session) {
    return (
      <div className="patron-account">
        <p>{t.signedInWith(session.kind)}</p>
        <details className="patron-data">
          <summary>{t.yourData}</summary>
          <p>
            {t.syncedNote} {session.kind === "card" ? t.pinNote : t.emailNote} {t.sessionNote}
          </p>
          <ConfirmButton
            label={t.deleteSynced}
            confirmLabel={t.deleteSyncedConfirm}
            onConfirm={() => deleteSyncedHistory(session)}
          />
        </details>
        <button
          type="button"
          className="patron-link"
          onClick={() => {
            signOut();
            onSessionChange(null);
          }}
        >
          {t.signOut}
        </button>
      </div>
    );
  }

  if (methods.length === 0) return null;

  if (!open) {
    return (
      <div className="patron-account">
        <button type="button" className="patron-link" onClick={() => setOpen(true)}>
          {methods.includes("card") ? t.signInWithCard : t.signIn}
        </button>
        <p className="patron-hint">{t.signInOptional}</p>
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
      setStatus(t.checkEmail);
    } catch (error) {
      setStatus((error as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="patron-account" aria-label={t.signIn}>
      {methods.includes("card") && (
        <form onSubmit={cardSubmit}>
          <label htmlFor="patron-card">{t.cardNumber}</label>
          <input
            id="patron-card"
            inputMode="numeric"
            autoComplete="username"
            required
            value={card}
            onChange={(e) => setCard(e.target.value)}
          />
          <label htmlFor="patron-pin">{t.pin}</label>
          <input
            id="patron-pin"
            type="password"
            autoComplete="current-password"
            required
            value={pin}
            onChange={(e) => setPin(e.target.value)}
          />
          <button type="submit" disabled={busy}>
            {t.signIn}
          </button>
        </form>
      )}
      {methods.includes("email") && (
        <form onSubmit={emailSubmit}>
          <label htmlFor="patron-email">{methods.includes("card") ? t.orEmail : t.email}</label>
          <input
            id="patron-email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <button type="submit" disabled={busy}>
            {t.emailMe}
          </button>
        </form>
      )}
      <p role="status">{status}</p>
      <button type="button" className="patron-link" onClick={() => setOpen(false)}>
        {t.continueWithout}
      </button>
    </section>
  );
}
