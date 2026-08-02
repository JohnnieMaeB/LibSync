"""Routes for the /chat endpoints (single-shot and streamed)."""

import json
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.agent import get_chat_reply, stream_chat_reply
from app.rate_limit import RATE_LIMIT, limiter

router = APIRouter()


@router.post("/chat")
@limiter.limit(RATE_LIMIT)
async def chat(request: Request):
    message, session_id = await _parse_chat_request(request)
    if not message:
        return JSONResponse(status_code=400, content={"error": "No message provided"})

    try:
        reply = await get_chat_reply(message, request.app.state.http_client, session_id)
        return {"reply": reply, "session_id": session_id}
    except Exception:
        return JSONResponse(
            status_code=500,
            content={"error": "⚠️ Error: Unable to reach AI service. Please try again later."},
        )


@router.post("/chat/stream")
@limiter.limit(RATE_LIMIT)
async def chat_stream(request: Request):
    message, session_id = await _parse_chat_request(request)
    if not message:
        return JSONResponse(status_code=400, content={"error": "No message provided"})

    http_client = request.app.state.http_client

    async def event_source():
        yield _format_sse("session", {"session_id": session_id})
        async for event_name, data in stream_chat_reply(message, http_client, session_id):
            yield _format_sse(event_name, data)

    return StreamingResponse(event_source(), media_type="text/event-stream")


async def _parse_chat_request(request: Request) -> tuple[str | None, str]:
    """Returns (message, session_id). `message` is None if missing/invalid.

    Clients mint their own session id (crypto.randomUUID(), persisted in
    localStorage); one is minted server-side as a fallback so callers that
    don't send one still get history continuity from their second request on.
    """
    body = None
    if await _has_json_body(request):
        try:
            body = await request.json()
        except ValueError:
            body = None
    message = body.get("message") if isinstance(body, dict) else None
    session_id = body.get("session_id") if isinstance(body, dict) else None

    if not session_id or not isinstance(session_id, str):
        session_id = str(uuid.uuid4())

    return message, session_id


def _format_sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _has_json_body(request: Request) -> bool:
    content_type = request.headers.get("content-type", "")
    if "application/json" not in content_type:
        return False
    body = await request.body()
    return bool(body)
