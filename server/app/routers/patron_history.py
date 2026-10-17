"""Synced chat history for signed-in patrons — Tier 9 Phase 37 (TIER9_PLAN.md §2.2).

GET    /patron/conversations        the patron's conversations (expired ones purged first)
PUT    /patron/conversations/{id}   save one
DELETE /patron/conversations/{id}   delete one
DELETE /patron/conversations        delete all of them

Every route needs a valid patron session (X-LibSync-Patron) and only ever
touches that patron's rows. Anonymous patrons never reach this: their
history stays in their own browser.
"""

from datetime import UTC, datetime, timedelta

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app import patron_auth
from app.config import SUPABASE_URL
from app.library_config import _headers, supabase_enabled
from app.rate_limit import RATE_LIMIT, limiter

router = APIRouter(prefix="/patron/conversations")

RETENTION_DAYS = 90
MAX_CONVERSATIONS = 200
MAX_CONVERSATION_BYTES = 256 * 1024


class ConversationBody(BaseModel):
    title: str = Field(max_length=200)
    createdAt: int
    updatedAt: int
    entries: list = Field(max_length=500)


def _session(request: Request) -> patron_auth.PatronSession:
    if not supabase_enabled():
        raise HTTPException(status_code=404, detail="Synced history isn't available here.")
    session = patron_auth.verify(request.headers.get("x-libsync-patron"))
    if session is None:
        raise HTTPException(status_code=401, detail="Sign in to sync your history.")
    return session


async def _rest(request: Request, method: str, **kwargs) -> httpx.Response:
    client: httpx.AsyncClient = request.app.state.http_client
    headers = {**_headers(), **kwargs.pop("extra_headers", {})}
    response = await client.request(
        method, f"{SUPABASE_URL}/rest/v1/patron_conversations", headers=headers, timeout=10.0, **kwargs
    )
    response.raise_for_status()
    return response


def _mine(session: patron_auth.PatronSession) -> dict[str, str]:
    return {"patron_ref": f"eq.{session.patron_ref}", "library_id": f"eq.{session.library_id}"}


@router.get("")
@limiter.limit(RATE_LIMIT)
async def list_conversations(request: Request):
    session = _session(request)
    cutoff = (datetime.now(UTC) - timedelta(days=RETENTION_DAYS)).isoformat()
    await _rest(request, "DELETE", params={**_mine(session), "updated_at": f"lt.{cutoff}"})
    rows = (
        await _rest(
            request,
            "GET",
            params={**_mine(session), "select": "id,title,created_at_ms,updated_at_ms,entries", "order": "updated_at_ms.desc"},
        )
    ).json()
    return [
        {"id": r["id"], "title": r["title"], "createdAt": r["created_at_ms"], "updatedAt": r["updated_at_ms"], "entries": r["entries"]}
        for r in rows
    ]


@router.put("/{conversation_id}")
@limiter.limit("300/15 minutes")
async def save_conversation(request: Request, conversation_id: str, body: ConversationBody):
    session = _session(request)
    if len(body.model_dump_json()) > MAX_CONVERSATION_BYTES:
        raise HTTPException(status_code=413, detail="That conversation is too long to sync.")
    existing = (await _rest(request, "GET", params={**_mine(session), "select": "id"})).json()
    if conversation_id not in {r["id"] for r in existing} and len(existing) >= MAX_CONVERSATIONS:
        raise HTTPException(status_code=409, detail=f"You can sync up to {MAX_CONVERSATIONS} conversations.")
    await _rest(
        request,
        "POST",
        json={
            "patron_ref": session.patron_ref,
            "library_id": session.library_id,
            "id": conversation_id[:100],
            "title": body.title,
            "created_at_ms": body.createdAt,
            "updated_at_ms": body.updatedAt,
            "entries": body.entries,
            "updated_at": datetime.now(UTC).isoformat(),
        },
        extra_headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
    )
    return {"saved": conversation_id}


@router.delete("/{conversation_id}")
@limiter.limit(RATE_LIMIT)
async def delete_conversation(request: Request, conversation_id: str):
    session = _session(request)
    await _rest(request, "DELETE", params={**_mine(session), "id": f"eq.{conversation_id}"})
    return {"deleted": conversation_id}


@router.delete("")
@limiter.limit(RATE_LIMIT)
async def delete_all(request: Request):
    session = _session(request)
    await _rest(request, "DELETE", params=_mine(session))
    return {"deleted": "all"}
