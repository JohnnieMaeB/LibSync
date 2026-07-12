"""Client for the Open Library API — free, no API key required.

See https://openlibrary.org/developers/api. Uses the Search API for
title/author lookups, the Read/Availability API for per-edition lending
status, and the Covers API for cover image URLs.
"""

import time

import httpx

SEARCH_URL = "https://openlibrary.org/search.json"
AVAILABILITY_URL = "https://openlibrary.org/api/volumes/brief/olid/{olid}.json"
COVER_URL = "https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"
WORK_URL = "https://openlibrary.org{key}"

# Open Library asks anonymous callers to identify themselves via User-Agent;
# doing so raises the courtesy rate limit from 1 req/s to 3 req/s.
USER_AGENT = "LibSync/1.0 (https://github.com/JohnnieMaeB/LibSync)"

_CACHE_TTL_SECONDS = 300
_cache: dict[str, tuple[float, list[dict]]] = {}


async def search_catalog(client: httpx.AsyncClient, query: str, limit: int = 3) -> list[dict]:
    """Search Open Library for books matching a title/author query.

    Returns a list of dicts: title, author, first_publish_year, cover_url,
    url (the work's Open Library page, for a real link-out), and
    availability (one of the Read API's status strings — "full access",
    "lendable", "checked out", "restricted" — or "not available online" /
    "unknown"). Results are cached in-process for a few minutes so repeated
    questions in a conversation don't hammer the free, unauthenticated API.
    """
    cache_key = f"{query.strip().lower()}:{limit}"
    cached = _cache.get(cache_key)
    if cached and time.monotonic() - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]

    response = await client.get(
        SEARCH_URL,
        params={
            "q": query,
            "fields": "title,author_name,first_publish_year,cover_i,key,edition_key,ebook_access",
            "limit": limit,
        },
        headers={"User-Agent": USER_AGENT},
    )
    response.raise_for_status()
    docs = response.json().get("docs", [])

    results = []
    for doc in docs:
        cover_i = doc.get("cover_i")
        edition_keys = doc.get("edition_key") or []
        availability = (
            await _check_availability(client, edition_keys[0])
            if edition_keys
            else _availability_from_search_doc(doc)
        )
        key = doc.get("key")
        results.append(
            {
                "title": doc.get("title", "Unknown title"),
                "author": ", ".join(doc.get("author_name", [])) or "Unknown author",
                "first_publish_year": doc.get("first_publish_year"),
                "cover_url": COVER_URL.format(cover_id=cover_i) if cover_i else None,
                "url": WORK_URL.format(key=key) if key else None,
                "availability": availability,
            }
        )

    _cache[cache_key] = (time.monotonic(), results)
    return results


def _availability_from_search_doc(doc: dict) -> str:
    ebook_access = doc.get("ebook_access")
    if ebook_access in ("public", "borrowable"):
        return ebook_access
    return "not available online"


async def _check_availability(client: httpx.AsyncClient, edition_olid: str) -> str:
    try:
        response = await client.get(
            AVAILABILITY_URL.format(olid=edition_olid),
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
        items = response.json().get("items") or []
        if items:
            return items[0].get("status", "unknown")
    except Exception as error:
        print("Open Library availability check failed:", error)
    return "unknown"
