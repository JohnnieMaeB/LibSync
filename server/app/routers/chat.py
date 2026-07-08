"""Routes for the /chat endpoint."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.agent import get_chat_reply
from app.rate_limit import RATE_LIMIT, limiter

router = APIRouter()


@router.post("/chat")
@limiter.limit(RATE_LIMIT)
async def chat(request: Request):
    body = None
    if await _has_json_body(request):
        try:
            body = await request.json()
        except ValueError:
            body = None
    message = body.get("message") if isinstance(body, dict) else None

    if not message:
        return JSONResponse(status_code=400, content={"error": "No message provided"})

    try:
        reply = await get_chat_reply(message)
        return {"reply": reply}
    except Exception:
        return JSONResponse(
            status_code=500,
            content={"error": "⚠️ Error: Unable to reach AI service. Please try again later."},
        )


async def _has_json_body(request: Request) -> bool:
    content_type = request.headers.get("content-type", "")
    if "application/json" not in content_type:
        return False
    body = await request.body()
    return bool(body)
