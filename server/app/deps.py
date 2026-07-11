"""Shared dependencies injected into PydanticAI tool calls via RunContext."""

from dataclasses import dataclass

import httpx


@dataclass
class LibSyncDeps:
    http_client: httpx.AsyncClient
