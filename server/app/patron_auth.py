"""Patron sessions — Tier 9 Phase 36 (TIER9_PLAN.md §2.1).

Two ways in, one session format:
- **Library card** (default): card number + PIN, checked by the library's own
  ILS over SIP2 (app/services/sip2.py).
- **Email** (fallback for libraries without SIP2): a Supabase magic link.

Either way, LibSync issues its own session token: Fernet (AES + HMAC), so it
is opaque to the browser and tamper-proof. It carries the library id, a
stable patron reference (an HMAC of the card or Supabase user id, not
reversible without the server's secret), the sign-in kind, and, for card
sessions only, the card number, encrypted inside the token so the account
features can look a patron up later without LibSync storing it anywhere.
The PIN is never stored, logged or put in the token.

Needs PATRON_SESSION_SECRET (any long random string). Without it, patron
sign-in is off and everything else is unchanged.
"""

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass

from cryptography.fernet import Fernet, InvalidToken

from app.config import PATRON_SESSION_SECRET

SESSION_TTL_SECONDS = 12 * 60 * 60


@dataclass(frozen=True)
class PatronSession:
    library_id: str
    patron_ref: str
    kind: str  # "card" or "email"
    card: str | None = None
    expires_at: int = 0


def sessions_enabled() -> bool:
    return bool(PATRON_SESSION_SECRET)


def _fernet() -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(f"session:{PATRON_SESSION_SECRET}".encode()).digest())
    return Fernet(key)


def patron_ref(library_id: str, identity: str) -> str:
    """Stable per library and identity; meaningless without the server secret."""
    digest = hmac.new(f"ref:{PATRON_SESSION_SECRET}".encode(), f"{library_id}:{identity}".encode(), hashlib.sha256)
    return digest.hexdigest()[:32]


def issue(library_id: str, kind: str, identity: str, card: str | None = None) -> tuple[str, PatronSession]:
    session = PatronSession(
        library_id=library_id,
        patron_ref=patron_ref(library_id, identity),
        kind=kind,
        card=card,
        expires_at=int(time.time()) + SESSION_TTL_SECONDS,
    )
    payload = {"lib": session.library_id, "ref": session.patron_ref, "kind": kind, "exp": session.expires_at}
    if card:
        payload["card"] = card
    return _fernet().encrypt(json.dumps(payload).encode()).decode(), session


def verify(token: str | None) -> PatronSession | None:
    """The session a token carries, or None if missing, forged, or expired."""
    if not token or not sessions_enabled():
        return None
    try:
        payload = json.loads(_fernet().decrypt(token.encode(), ttl=SESSION_TTL_SECONDS))
    except (InvalidToken, ValueError):
        return None
    if payload.get("exp", 0) < time.time():
        return None
    return PatronSession(
        library_id=payload["lib"],
        patron_ref=payload["ref"],
        kind=payload["kind"],
        card=payload.get("card"),
        expires_at=payload["exp"],
    )
