"""OverDrive (Libby) availability for a library's own digital collection —
Tier 8 Phase 37T (TIER8_PLAN.md §2.7).

Uses OverDrive's Discovery APIs with client authentication (search, metadata
and availability; no patron data): a client-credentials token, the library's
collection token, a product search, and each product's availability link.
Requires the operator to be an approved OverDrive developer partner and the
library's OverDrive library id.

**Not yet verified against the live API**: written to OverDrive's documented
Discovery API and covered by mocked tests.

integrations.overdrive: {"library_id": "...", "client_id": "..."}
secret: library_secrets.overdrive_client_secret
"""

import time

import httpx

TOKEN_URL = "https://oauth.overdrive.com/token"
API_BASE = "https://api.overdrive.com/v1"

_token_cache: dict[str, tuple[float, str]] = {}
_collection_cache: dict[str, str] = {}


async def _token(client: httpx.AsyncClient, client_id: str, client_secret: str) -> str:
    cached = _token_cache.get(client_id)
    if cached and cached[0] > time.monotonic():
        return cached[1]
    response = await client.post(
        TOKEN_URL,
        auth=(client_id, client_secret),
        data={"grant_type": "client_credentials"},
        timeout=10.0,
    )
    response.raise_for_status()
    body = response.json()
    _token_cache[client_id] = (time.monotonic() + max(int(body.get("expires_in", 3600)) - 60, 0), body["access_token"])
    return body["access_token"]


async def _collection_token(client: httpx.AsyncClient, headers: dict, library_id: str) -> str:
    if library_id not in _collection_cache:
        response = await client.get(f"{API_BASE}/libraries/{library_id}", headers=headers, timeout=10.0)
        response.raise_for_status()
        _collection_cache[library_id] = response.json()["collectionToken"]
    return _collection_cache[library_id]


async def search_availability(
    client: httpx.AsyncClient, settings: dict, client_secret: str | None, query: str, limit: int = 3
) -> list[dict]:
    library_id = settings.get("library_id")
    client_id = settings.get("client_id")
    if not library_id or not client_id or not client_secret:
        raise ValueError("OverDrive needs integrations.overdrive.library_id, client_id and the overdrive_client_secret")
    headers = {"Authorization": f"Bearer {await _token(client, client_id, client_secret)}"}
    collection = await _collection_token(client, headers, str(library_id))
    response = await client.get(
        f"{API_BASE}/collections/{collection}/products",
        params={"q": query.strip(), "limit": str(limit)},
        headers=headers,
        timeout=10.0,
    )
    response.raise_for_status()

    results = []
    for product in (response.json().get("products") or [])[:limit]:
        availability_href = ((product.get("links") or {}).get("availability") or {}).get("href")
        availability = {}
        if availability_href:
            availability_response = await client.get(availability_href, headers=headers, timeout=10.0)
            if availability_response.status_code == 200:
                availability = availability_response.json()
        results.append(
            {
                "title": product.get("title") or "Untitled",
                "creator": (product.get("primaryCreator") or {}).get("name"),
                "formats": [f.get("name") for f in product.get("formats") or [] if f.get("name")],
                "copies_available": availability.get("copiesAvailable"),
                "copies_owned": availability.get("copiesOwned"),
                "holds": availability.get("numberOfHolds"),
            }
        )
    return results
