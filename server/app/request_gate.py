"""Per-request library checks shared by /agent, /chat and /chat/stream.

Combines Tier 6's widget registration, the embed snippet's tool switches
(Phase 36T) and, when Supabase is configured, the library's dashboard
settings (Phase 30). With no Supabase, or no row for this library, the result
is exactly the pre-Phase-30 behavior.
"""

from dataclasses import dataclass

from fastapi import Request
from fastapi.responses import JSONResponse

from app import patron_auth
from app.api_keys import library_for_key
from app.library_config import LibraryConfig, effective_tools, get_library_config
from app.tenants import normalize_library_id, parse_enabled_tools
from app.widget_registry import check_widget_registration

AI_DISABLED_MESSAGE = "This library has turned the AI assistant off. Please contact library staff for help."
ORIGIN_NOT_ALLOWED_MESSAGE = "This website isn't set up to use this library's assistant."


@dataclass(frozen=True)
class RequestLibrary:
    library_id: str | None
    enabled_tools: frozenset[str] | None
    config: LibraryConfig | None
    patron: patron_auth.PatronSession | None = None


async def gate_request(request: Request) -> RequestLibrary | JSONResponse:
    api_key = request.headers.get("x-libsync-key")
    if api_key:
        return await _gate_api_key(request, api_key)

    raw_library = request.headers.get("x-libsync-library")
    origin = request.headers.get("origin")
    library_id = normalize_library_id(raw_library)
    config = await get_library_config(request.app.state.http_client, library_id)

    if config is not None:
        if not config.ai_enabled:
            return JSONResponse(
                status_code=403,
                content={"error": AI_DISABLED_MESSAGE, "code": "ai_disabled", "help_url": config.help_url},
            )
        if config.allowed_origins is not None and origin not in config.allowed_origins:
            return JSONResponse(status_code=403, content={"error": ORIGIN_NOT_ALLOWED_MESSAGE, "code": "origin"})
        # A library configured in the dashboard is registered by definition;
        # Tier 6's in-memory grace quota only governs unknown embeds.
    else:
        registration_error = check_widget_registration(raw_library, origin)
        if registration_error:
            return JSONResponse(status_code=403, content={"error": registration_error})

    header_tools = parse_enabled_tools(request.headers.get("x-libsync-tools"))
    # A patron session only counts for the library it was issued for.
    patron = patron_auth.verify(request.headers.get("x-libsync-patron"))
    if patron is not None and patron.library_id != library_id:
        patron = None
    return RequestLibrary(library_id, effective_tools(header_tools, config), config, patron)


async def _gate_api_key(request: Request, api_key: str) -> RequestLibrary | JSONResponse:
    """Server-to-server calls (Phase 34): the key decides the library, so the
    browser-only checks (origin allowlist, widget registration) don't apply,
    but a library that switched its assistant off stays off."""
    client = request.app.state.http_client
    library_id = await library_for_key(client, api_key)
    if library_id is None:
        return JSONResponse(status_code=401, content={"error": "Invalid or revoked API key.", "code": "api_key"})
    config = await get_library_config(client, library_id)
    if config is not None and not config.ai_enabled:
        return JSONResponse(
            status_code=403,
            content={"error": AI_DISABLED_MESSAGE, "code": "ai_disabled", "help_url": config.help_url},
        )
    header_tools = parse_enabled_tools(request.headers.get("x-libsync-tools"))
    return RequestLibrary(library_id, effective_tools(header_tools, config), config)
