"""Verifies that a request comes from a signed-in staff member of a library —
for the dashboard's backend endpoints (Tier 8 Phase 31+).

The dashboard sends the staff member's Supabase access token. We confirm it
with Supabase Auth (which also catches expired and revoked sessions), then
check `library_staff` with the server's secret key. An explicit membership
check, rather than relying on row-level security, because the secret key
bypasses RLS.
"""

from dataclasses import dataclass

import httpx
from fastapi import HTTPException, Request

from app.config import SUPABASE_SECRET_KEY, SUPABASE_URL
from app.library_config import _headers, supabase_enabled


@dataclass(frozen=True)
class StaffMember:
    user_id: str
    email: str | None
    role: str


async def require_staff(request: Request, library_id: str, admin: bool = False) -> StaffMember:
    if not supabase_enabled():
        raise HTTPException(status_code=503, detail="The staff dashboard isn't set up for this deployment.")
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Sign in to the staff dashboard first.")
    token = auth.split(" ", 1)[1]

    client: httpx.AsyncClient = request.app.state.http_client
    try:
        user_response = await client.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={"apikey": SUPABASE_SECRET_KEY or "", "Authorization": f"Bearer {token}"},
            timeout=5.0,
        )
    except httpx.HTTPError as error:
        raise HTTPException(status_code=503, detail="Couldn't reach the sign-in service. Try again.") from error
    if user_response.status_code != 200:
        raise HTTPException(status_code=401, detail="Your session has expired. Sign in again.")
    user = user_response.json()

    try:
        staff_response = await client.get(
            f"{SUPABASE_URL}/rest/v1/library_staff",
            params={"library_id": f"eq.{library_id}", "user_id": f"eq.{user['id']}", "select": "role"},
            headers=_headers(),
            timeout=5.0,
        )
        staff_response.raise_for_status()
        rows = staff_response.json()
    except httpx.HTTPError as error:
        raise HTTPException(status_code=503, detail="Couldn't check your library access. Try again.") from error
    if not rows or (admin and rows[0]["role"] != "admin"):
        raise HTTPException(status_code=403, detail="You don't have access to this library's settings.")
    return StaffMember(user_id=user["id"], email=user.get("email"), role=rows[0]["role"])
