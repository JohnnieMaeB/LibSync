"""Developer surface and patron feedback — Tier 8 Phase 34 (TIER8_PLAN.md §2.5).

POST   /admin/libraries/{id}/api-keys        create a key (admins; shown once)
GET    /admin/libraries/{id}/api-keys        list keys (prefix, name, dates)
DELETE /admin/libraries/{id}/api-keys/{key}  revoke
POST   /feedback                             a patron's "not helpful" report,
                                             forwarded to the library's webhook
"""

import uuid
from datetime import UTC, datetime

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app import api_keys
from app.config import SUPABASE_URL
from app.library_config import _headers, get_library_config
from app.rate_limit import RATE_LIMIT, limiter
from app.staff_auth import require_staff
from app.tenants import normalize_library_id

router = APIRouter()


class NewKey(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class Feedback(BaseModel):
    question: str = Field(max_length=4000)
    answer: str = Field(max_length=8000)


def _library(library_id: str) -> str:
    normalized = normalize_library_id(library_id)
    if normalized is None:
        raise HTTPException(status_code=404, detail="Unknown library.")
    return normalized


async def _rest(request: Request, method: str, path: str, **kwargs) -> httpx.Response:
    client: httpx.AsyncClient = request.app.state.http_client
    response = await client.request(method, f"{SUPABASE_URL}/rest/v1/{path}", headers=_headers(), timeout=10.0, **kwargs)
    response.raise_for_status()
    return response


@router.post("/admin/libraries/{library_id}/api-keys")
@limiter.limit("20/hour")
async def create_api_key(request: Request, library_id: str, body: NewKey):
    library_id = _library(library_id)
    staff = await require_staff(request, library_id, admin=True)
    key, digest, prefix = api_keys.generate_key()
    key_id = str(uuid.uuid4())
    await _rest(
        request,
        "POST",
        "library_api_keys",
        json={"id": key_id, "library_id": library_id, "name": body.name.strip(), "key_hash": digest, "prefix": prefix, "created_by": staff.user_id},
    )
    return {"id": key_id, "name": body.name.strip(), "prefix": prefix, "key": key}


@router.get("/admin/libraries/{library_id}/api-keys")
@limiter.limit(RATE_LIMIT)
async def list_api_keys(request: Request, library_id: str):
    library_id = _library(library_id)
    await require_staff(request, library_id)
    response = await _rest(
        request,
        "GET",
        "library_api_keys",
        params={"library_id": f"eq.{library_id}", "select": "id,name,prefix,created_at,revoked_at", "order": "created_at.desc"},
    )
    return response.json()


@router.delete("/admin/libraries/{library_id}/api-keys/{key_id}")
@limiter.limit(RATE_LIMIT)
async def revoke_api_key(request: Request, library_id: str, key_id: str):
    library_id = _library(library_id)
    await require_staff(request, library_id, admin=True)
    await _rest(
        request,
        "PATCH",
        "library_api_keys",
        params={"id": f"eq.{key_id}", "library_id": f"eq.{library_id}"},
        json={"revoked_at": datetime.now(UTC).isoformat()},
    )
    api_keys.reset_cache()  # immediate in this process; others within a minute
    return {"revoked": key_id}


@router.post("/feedback")
@limiter.limit("10/hour")
async def send_feedback(request: Request, body: Feedback):
    """Forwards a patron's explicit "not helpful" report to the library's own
    webhook. Nothing is stored by LibSync; without a webhook it's a 404 and the
    app doesn't offer the button."""
    library_id = normalize_library_id(request.headers.get("x-libsync-library"))
    client: httpx.AsyncClient = request.app.state.http_client
    config = await get_library_config(client, library_id)
    if config is None or not config.feedback_webhook:
        raise HTTPException(status_code=404, detail="This library doesn't collect feedback.")
    payload = {
        "library_id": config.id,
        "type": "not_helpful",
        "question": body.question,
        "answer": body.answer,
        "received_at": datetime.now(UTC).isoformat(),
    }
    try:
        response = await client.post(config.feedback_webhook, json=payload, timeout=5.0)
        response.raise_for_status()
    except Exception as error:
        print("Feedback webhook failed:", error)
        raise HTTPException(status_code=502, detail="Couldn't send that to library staff. Try again later.") from error
    return {"sent": True}
