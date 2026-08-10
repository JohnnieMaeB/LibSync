"""Route for the Tier 6 embeddable widget's lightweight registration step
(TIER6_PLAN.md §4/§5) — no billing, no real multi-tenant auth, just an
allowlist a library claims once so its embed stops burning its free grace
quota (see app/widget_registry.py)."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.rate_limit import RATE_LIMIT, limiter
from app.schemas import WidgetRegisterRequest
from app.widget_registry import widget_registry

router = APIRouter()


@router.post("/widget/register")
@limiter.limit(RATE_LIMIT)
async def register_widget(request: Request, payload: WidgetRegisterRequest):
    library_id = (payload.library_id or "").strip()
    if not library_id:
        return JSONResponse(status_code=400, content={"error": "library_id is required."})

    origin = request.headers.get("origin")
    if not origin:
        return JSONResponse(
            status_code=400,
            content={"error": "Registration requires an Origin header (call this from the embedding page)."},
        )

    claimed = widget_registry.register(library_id, origin)
    if not claimed:
        return JSONResponse(
            status_code=409,
            content={"error": f"library_id '{library_id}' is already registered to a different origin."},
        )

    return {"library_id": library_id, "origin": origin, "registered": True}
