"""Shared rate limiter, matching the original express-rate-limit configuration
(100 requests per 15 minutes per client IP).

Tier 6 (embeddable widget) adds a second dimension: per-IP alone isn't
enough once the backend is reachable from any site that adds the embed
snippet, since many patrons behind different IPs can share one embedding
origin. `WIDGET_ORIGIN_RATE_LIMIT` bounds total traffic from a single
`Origin` header, so one misbehaving or abusive embed can't consume the
whole free-tier Groq/Pinecone/Render budget out from under every other
library using the widget (TIER6_PLAN.md §4) — stacked as a second
`@limiter.limit(...)` decorator alongside the existing per-IP one (slowapi
evaluates every limit registered for a route on each request; see
routers/agent.py and routers/chat.py), not a separate Limiter instance.
"""

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

RATE_LIMIT = "100/15 minutes"
WIDGET_ORIGIN_RATE_LIMIT = "500/15 minutes"

limiter = Limiter(key_func=get_remote_address)


def get_origin_or_ip(request: Request) -> str:
    """Keys on the `Origin` header when present (browser requests, including
    every embedded widget), falling back to remote address for non-browser
    callers that don't send one."""
    return request.headers.get("origin") or get_remote_address(request)
