"""Shared dependencies injected into PydanticAI tool calls via RunContext."""

from dataclasses import dataclass

import httpx


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
