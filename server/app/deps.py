"""Shared dependencies injected into PydanticAI tool calls via RunContext."""

from dataclasses import dataclass

import httpx

from app.library_config import LibraryConfig
from app.patron_auth import PatronSession


@dataclass
class LibSyncDeps:
    http_client: httpx.AsyncClient
    # The embedding library (Tier 6's `X-LibSync-Library` header, validated
    # by app.tenants.normalize_library_id), or None for the standalone app.
    library_id: str | None = None
    # Tool groups the embedding library allows (app.tenants.parse_enabled_tools),
    # or None for all of them. TIER8_PLAN.md §2.8: a library can switch AI
    # features off.
    enabled_tools: frozenset[str] | None = None
    # The library's dashboard settings (Tier 8 Phase 30), or None — drives the
    # catalog driver (Phase 32).
    library_config: LibraryConfig | None = None
    # Tier 9: the signed-in patron, if any (and only for this library).
    patron: PatronSession | None = None
