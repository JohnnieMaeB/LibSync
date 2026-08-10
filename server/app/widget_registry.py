"""In-memory library-id -> origin allowlist for the Tier 6 embeddable widget.

Render's free instance has no durable disk, so — like session_store.py —
this deliberately trades persistence for staying at $0/month: registrations
reset on cold start. Registration is a lightweight speed bump, not real
multi-tenant auth (TIER6_PLAN.md §4/§5): a small per-origin grace quota lets
a freshly-embedded widget work immediately, then nudges unregistered
origins toward POST /widget/register before cutting them off, rather than
requiring registration up front.
"""

from dataclasses import dataclass

GRACE_LIMIT = 50


@dataclass
class _GraceCounter:
    remaining: int


class WidgetRegistry:
    def __init__(self, grace_limit: int = GRACE_LIMIT):
        self._by_library: dict[str, str] = {}  # library_id -> claiming origin
        self._grace: dict[str, _GraceCounter] = {}  # origin -> counter
        self._grace_limit = grace_limit

    def register(self, library_id: str, origin: str) -> bool:
        """Claims `library_id` for `origin`. Returns False only if another
        origin already claimed this id; re-registering the same pair (or a
        first-time registration) succeeds."""
        existing = self._by_library.get(library_id)
        if existing is not None and existing != origin:
            return False
        self._by_library[library_id] = origin
        return True

    def is_registered(self, library_id: str, origin: str) -> bool:
        return self._by_library.get(library_id) == origin

    def consume_grace(self, origin: str) -> int:
        """Consumes one grace-quota unit for an unregistered origin, returning
        the remaining count, or -1 once the quota is exhausted (caller should
        reject the request in that case)."""
        counter = self._grace.setdefault(origin, _GraceCounter(self._grace_limit))
        if counter.remaining <= 0:
            return -1
        counter.remaining -= 1
        return counter.remaining

    def reset(self) -> None:
        """Test hygiene only — clears all claims and grace counters."""
        self._by_library.clear()
        self._grace.clear()


widget_registry = WidgetRegistry()


def check_widget_registration(library_id: str | None, origin: str | None) -> str | None:
    """Returns an error message if a widget-originated request should be
    rejected, or None if it's clear to proceed.

    Requests with no `library_id` (the standalone app, direct API callers)
    are always untouched — this only governs the embeddable-widget path
    Tier 6 adds, identified by the `X-LibSync-Library` header the widget's
    frontend sends (see app/src/hooks/useAgentStream.ts).
    """
    if not library_id:
        return None
    request_origin = origin or "unknown"
    if widget_registry.is_registered(library_id, request_origin):
        return None
    remaining = widget_registry.consume_grace(request_origin)
    if remaining < 0:
        return (
            f"Unregistered LibSync widget library '{library_id}' has used its free grace quota. "
            "Register it via POST /widget/register before continuing."
        )
    return None
