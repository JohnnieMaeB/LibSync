"""Per-library (tenant) resolution — Tier 8 groundwork (TIER8_PLAN.md §2.1).

A library is identified by the `X-LibSync-Library` header Tier 6's widget
already sends. Each library's policy documents live in their own Pinecone
namespace, named after its library id — Pinecone's documented pattern for
multi-tenant RAG (physical isolation; delete the namespace to offboard).

Until a library has uploaded its own documents (Tier 8 Phase 31), it has no
namespace yet, and gets the shared demo policies in DEFAULT_NAMESPACE. That
switch-over is automatic: once a namespace with the library's id exists in
the index, its patrons get its policies — no tenant config to keep in sync.
"""

import re
import time

from app.services.pinecone_service import DEFAULT_NAMESPACE, list_namespaces

# Lowercase slug, as Tier 6's `data-library` attribute is documented. Anything
# else is treated as "no library" rather than passed through, so a crafted
# header can't select an arbitrary namespace.
_LIBRARY_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")

_NAMESPACE_CACHE_TTL_SECONDS = 300
_namespace_cache: tuple[float, frozenset[str]] | None = None


def normalize_library_id(raw: str | None) -> str | None:
    """The library id from a request header, or None if absent or malformed."""
    if not raw:
        return None
    library_id = raw.strip().lower()
    return library_id if _LIBRARY_ID_PATTERN.fullmatch(library_id) else None


def _known_namespaces() -> frozenset[str]:
    # Cached: this runs on every policy search, and the namespace list only
    # changes when a library's documents are (re)uploaded.
    global _namespace_cache
    now = time.monotonic()
    if _namespace_cache is None or now - _namespace_cache[0] > _NAMESPACE_CACHE_TTL_SECONDS:
        _namespace_cache = (now, frozenset(list_namespaces()))
    return _namespace_cache[1]


def policy_namespace(library_id: str | None) -> str:
    """The Pinecone namespace to search for this library's policies.

    Blocking (may call Pinecone on a cache miss) — call it from a worker
    thread, as the policy tool already does for the search itself.
    """
    if library_id and library_id in _known_namespaces():
        return library_id
    return DEFAULT_NAMESPACE


def reset_namespace_cache() -> None:
    """Test hygiene only."""
    global _namespace_cache
    _namespace_cache = None
