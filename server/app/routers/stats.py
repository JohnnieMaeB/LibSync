"""Per-library usage stats for the staff dashboard — Tier 8 Phase 33."""

from fastapi import APIRouter, HTTPException, Request

from app.rate_limit import RATE_LIMIT, limiter
from app.staff_auth import require_staff
from app.tenants import normalize_library_id
from app.usage_stats import library_stats, stats_enabled

router = APIRouter()


@router.get("/admin/libraries/{library_id}/stats")
@limiter.limit(RATE_LIMIT)
async def get_library_stats(request: Request, library_id: str, days: int = 30):
    normalized = normalize_library_id(library_id)
    if normalized is None:
        raise HTTPException(status_code=404, detail="Unknown library.")
    await require_staff(request, normalized)
    if not stats_enabled():
        raise HTTPException(status_code=503, detail="Usage statistics aren't set up (needs a Logfire read token).")
    try:
        return await library_stats(normalized, days)
    except Exception as error:
        print("Usage stats query failed:", error)
        raise HTTPException(status_code=502, detail="Couldn't load usage statistics right now.") from error
