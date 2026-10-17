"""Per-library API keys for server-to-server use — Tier 8 Phase 34
(TIER8_PLAN.md §2.5).

A key looks like `ls_<random>`. Only its SHA-256 hash and a short prefix are
stored (Supabase `library_api_keys`); the key itself is shown once, at
creation. A request carrying `X-LibSync-Key` acts for that key's library.
Lookups are cached briefly, including misses, so a bad key can't hammer
Supabase; revocation takes effect within the cache window.
"""

import hashlib
import secrets
import time

import httpx

from app.config import SUPABASE_URL
from app.library_config import _headers, supabase_enabled

KEY_PREFIX = "ls_"
_CACHE_TTL_SECONDS = 60
_cache: dict[str, tuple[float, str | None]] = {}


def generate_key() -> tuple[str, str, str]:
    """Returns (key, sha256 hash, display prefix)."""
    key = KEY_PREFIX + secrets.token_urlsafe(32)
    return key, hash_key(key), key[:10]


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


async def library_for_key(client: httpx.AsyncClient, key: str) -> str | None:
    """The library an active key belongs to, or None (unknown, revoked, or
    Supabase unreachable — a key can't be honored without it)."""
    if not key.startswith(KEY_PREFIX) or not supabase_enabled():
        return None
    digest = hash_key(key)
    now = time.monotonic()
    cached = _cache.get(digest)
    if cached and now - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]
    try:
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/library_api_keys",
            params={"key_hash": f"eq.{digest}", "revoked_at": "is.null", "select": "library_id"},
            headers=_headers(),
            timeout=5.0,
        )
        response.raise_for_status()
        rows = response.json()
    except Exception as error:
        print("API key lookup failed:", error)
        return None
    library_id = rows[0]["library_id"] if rows else None
    _cache[digest] = (now, library_id)
    return library_id


def reset_cache() -> None:
    """Test hygiene, and immediate effect for revocations made by this process."""
    _cache.clear()
