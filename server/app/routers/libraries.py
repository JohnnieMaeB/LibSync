"""Public per-library settings for the patron app (Tier 8 Phase 30).

The widget fetches this on load so a library's dashboard settings (name, help
link, assistant on/off) apply without editing its embed snippet. 404 whenever
there's nothing to report, including when Supabase isn't configured, so the
app falls back to the snippet's attributes.
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.library_config import get_library_config
from app.rate_limit import RATE_LIMIT, limiter
from app.routers.patrons import sign_in_methods
from app.tenants import normalize_library_id

router = APIRouter()


@router.get("/libraries/{library_id}")
@limiter.limit(RATE_LIMIT)
async def library_public_config(request: Request, library_id: str):
    config = await get_library_config(request.app.state.http_client, normalize_library_id(library_id))
    if config is None:
        return JSONResponse(status_code=404, content={"error": "No settings for this library."})
    # Tier 9: which patron sign-in options to offer (empty = anonymous only).
    return {**config.public(), "patron_sign_in": sign_in_methods(config)}
