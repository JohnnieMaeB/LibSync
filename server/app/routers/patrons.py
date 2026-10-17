"""Patron sign-in — Tier 9 Phase 36 (TIER9_PLAN.md §2.1).

POST /patron/sign-in/card    card + PIN, checked over SIP2 → LibSync session
POST /patron/email-link      email the patron a Supabase magic link
POST /patron/sign-in/email   exchange the magic link's Supabase token → session
GET  /patron/me              who the X-LibSync-Patron session belongs to

All are per library (X-LibSync-Library). Signing in is always optional:
nothing else in the app requires it.
"""

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

from app import patron_auth
from app.config import SUPABASE_SECRET_KEY, SUPABASE_URL
from app.library_config import LibraryConfig, get_library_config, get_library_secret, supabase_enabled
from app.rate_limit import limiter
from app.services.sip2 import SIP2Client, SIP2Error
from app.tenants import normalize_library_id

router = APIRouter(prefix="/patron")

NOT_RECOGNIZED = "That card number and PIN weren't recognized. Check them, or ask library staff."


class CardSignIn(BaseModel):
    card: str = Field(min_length=3, max_length=40)
    pin: str = Field(min_length=1, max_length=40)


class EmailLink(BaseModel):
    email: EmailStr
    redirect_to: str = Field(max_length=500)


class EmailSignIn(BaseModel):
    access_token: str = Field(max_length=4000)


def sign_in_methods(config: LibraryConfig | None) -> list[str]:
    """Which sign-in options the patron app should offer this library."""
    if config is None or not patron_auth.sessions_enabled():
        return []
    methods = []
    if config.integration("sip2"):
        methods.append("card")
    if supabase_enabled():
        methods.append("email")
    return methods


async def _library(request: Request) -> LibraryConfig:
    library_id = normalize_library_id(request.headers.get("x-libsync-library"))
    config = await get_library_config(request.app.state.http_client, library_id)
    if config is None or not patron_auth.sessions_enabled():
        raise HTTPException(status_code=404, detail="This library doesn't offer patron accounts.")
    return config


def _session_response(token: str, session: patron_auth.PatronSession) -> dict:
    return {"token": token, "kind": session.kind, "library_id": session.library_id, "expires_at": session.expires_at}


@router.post("/sign-in/card")
@limiter.limit("10/15 minutes")  # PIN guessing: 10 tries per IP per 15 minutes
async def sign_in_with_card(request: Request, body: CardSignIn):
    config = await _library(request)
    settings = config.integration("sip2")
    if not settings:
        raise HTTPException(status_code=404, detail="This library doesn't offer card sign-in yet.")
    card = body.card.strip()
    password = await get_library_secret(request.app.state.http_client, config.id, "sip2_password")
    try:
        async with SIP2Client(settings, password) as sip:
            status = await sip.verify_patron(card, body.pin)
    except (SIP2Error, OSError, TimeoutError) as error:
        print("SIP2 sign-in failed:", type(error).__name__)  # never log the card or PIN
        raise HTTPException(status_code=502, detail="The library's card system didn't respond. Try again later.") from error
    if not (status.valid_patron and status.valid_password):
        raise HTTPException(status_code=401, detail=NOT_RECOGNIZED)
    token, session = patron_auth.issue(config.id, "card", card, card=card)
    return _session_response(token, session)


@router.post("/email-link")
@limiter.limit("5/hour")
async def send_email_link(request: Request, body: EmailLink):
    """Creates the patron's account if needed (sign-up is closed to the public,
    so the backend does it with the secret key) and emails a magic link."""
    config = await _library(request)
    if "email" not in sign_in_methods(config):
        raise HTTPException(status_code=404, detail="Email sign-in isn't available here.")
    client: httpx.AsyncClient = request.app.state.http_client
    headers = {"apikey": SUPABASE_SECRET_KEY or "", "Authorization": f"Bearer {SUPABASE_SECRET_KEY}"}
    try:
        create = await client.post(
            f"{SUPABASE_URL}/auth/v1/admin/users",
            json={"email": body.email, "email_confirm": True, "app_metadata": {"role": "patron"}},
            headers=headers,
            timeout=10.0,
        )
        # 422 = the account already exists, which is fine.
        if create.status_code not in (200, 201, 422):
            create.raise_for_status()
        send = await client.post(
            f"{SUPABASE_URL}/auth/v1/otp",
            params={"redirect_to": body.redirect_to},
            json={"email": body.email, "create_user": False},
            headers={"apikey": SUPABASE_SECRET_KEY or ""},
            timeout=10.0,
        )
        send.raise_for_status()
    except httpx.HTTPError as error:
        print("Patron email link failed:", type(error).__name__)
        raise HTTPException(status_code=502, detail="Couldn't send the sign-in email. Try again later.") from error
    return {"sent": True}


@router.post("/sign-in/email")
@limiter.limit("20/hour")
async def sign_in_with_email(request: Request, body: EmailSignIn):
    config = await _library(request)
    client: httpx.AsyncClient = request.app.state.http_client
    try:
        response = await client.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={"apikey": SUPABASE_SECRET_KEY or "", "Authorization": f"Bearer {body.access_token}"},
            timeout=10.0,
        )
    except httpx.HTTPError as error:
        raise HTTPException(status_code=502, detail="Couldn't reach the sign-in service.") from error
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="That sign-in link has expired. Request a new one.")
    user = response.json()
    token, session = patron_auth.issue(config.id, "email", f"email:{user['id']}")
    return _session_response(token, session)


@router.get("/me")
async def me(request: Request):
    session = patron_auth.verify(request.headers.get("x-libsync-patron"))
    if session is None:
        raise HTTPException(status_code=401, detail="Not signed in.")
    return {"kind": session.kind, "library_id": session.library_id, "expires_at": session.expires_at}
