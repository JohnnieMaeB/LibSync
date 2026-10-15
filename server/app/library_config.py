"""Per-library settings from Supabase — Tier 8 Phase 30 (TIER8_PLAN.md §2.2).

Only active when SUPABASE_URL and SUPABASE_SECRET_KEY are configured. Without
them, or if Supabase is unreachable, every lookup returns None and the backend
behaves exactly as it did before Phase 30 (embed-snippet attributes only), so
a Supabase outage can never take the chat down.

Settings are cached briefly in-process: they change rarely, and a chat turn
shouldn't add a database round trip.
"""

import time
from dataclasses import dataclass

import httpx

from app.config import SUPABASE_SECRET_KEY, SUPABASE_URL

_CACHE_TTL_SECONDS = 60
_cache: dict[str, tuple[float, "LibraryConfig | None"]] = {}

_PUBLIC_COLUMNS = "id,name,help_url,enabled_tools,ai_enabled,allowed_origins,catalog_driver,catalog_config"


@dataclass(frozen=True)
class LibraryConfig:
    id: str
    name: str
    help_url: str | None = None
    enabled_tools: frozenset[str] | None = None
    ai_enabled: bool = True
    allowed_origins: frozenset[str] | None = None
    catalog_driver: str = "openlibrary"
    catalog_config: dict | None = None

    def public(self) -> dict:
        """What the patron app may see (never secrets or catalog config)."""
        return {
            "id": self.id,
            "name": self.name,
            "help_url": self.help_url,
            "enabled_tools": sorted(self.enabled_tools) if self.enabled_tools is not None else None,
            "ai_enabled": self.ai_enabled,
        }


def supabase_enabled() -> bool:
    return bool(SUPABASE_URL and SUPABASE_SECRET_KEY)


def _headers() -> dict[str, str]:
    headers = {"apikey": SUPABASE_SECRET_KEY or ""}
    # Legacy service_role keys are JWTs and also go in Authorization; the new
    # sb_secret_ keys are sent as `apikey` only.
    if (SUPABASE_SECRET_KEY or "").startswith("eyJ"):
        headers["Authorization"] = f"Bearer {SUPABASE_SECRET_KEY}"
    return headers


def _parse(row: dict) -> LibraryConfig:
    tools = row.get("enabled_tools")
    origins = row.get("allowed_origins")
    return LibraryConfig(
        id=row["id"],
        name=row.get("name") or row["id"],
        help_url=row.get("help_url"),
        enabled_tools=frozenset(tools) if tools is not None else None,
        ai_enabled=row.get("ai_enabled", True) is not False,
        allowed_origins=frozenset(origins) if origins else None,
        catalog_driver=row.get("catalog_driver") or "openlibrary",
        catalog_config=row.get("catalog_config") or {},
    )


async def get_library_config(client: httpx.AsyncClient, library_id: str | None) -> LibraryConfig | None:
    """The library's settings, or None if Supabase is off, the library isn't
    configured there, or the lookup fails (fail open to today's defaults)."""
    if not library_id or not supabase_enabled():
        return None
    now = time.monotonic()
    cached = _cache.get(library_id)
    if cached and now - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]
    try:
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/libraries",
            params={"id": f"eq.{library_id}", "select": _PUBLIC_COLUMNS},
            headers=_headers(),
            timeout=5.0,
        )
        response.raise_for_status()
        rows = response.json()
        config = _parse(rows[0]) if rows else None
    except Exception as error:
        print("Library config lookup failed, using defaults:", error)
        return None  # not cached, so a transient failure retries next request
    _cache[library_id] = (now, config)
    return config


async def get_library_secret(client: httpx.AsyncClient, library_id: str, name: str) -> str | None:
    """A stored integration credential, read with the secret key (the table
    has no read policy for signed-in staff). None if unavailable."""
    if not supabase_enabled():
        return None
    try:
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/library_secrets",
            params={"library_id": f"eq.{library_id}", "name": f"eq.{name}", "select": "value"},
            headers=_headers(),
            timeout=5.0,
        )
        response.raise_for_status()
        rows = response.json()
        return rows[0]["value"] if rows else None
    except Exception as error:
        print("Library secret lookup failed:", error)
        return None


def effective_tools(header_tools: frozenset[str] | None, config: LibraryConfig | None) -> frozenset[str] | None:
    """Both the embed snippet and the dashboard can only narrow the tool set."""
    configured = config.enabled_tools if config else None
    if header_tools is None:
        return configured
    if configured is None:
        return header_tools
    return header_tools & configured


def reset_cache() -> None:
    """Test hygiene only."""
    _cache.clear()
