"""Client for the OpenAlex API — free, keyless for the volumes LibSync needs.

See https://docs.openalex.org/. A `mailto=` param (and, if configured, an
`api_key=`) puts requests in OpenAlex's "polite pool" for higher, more
reliable rate limits — same courtesy pattern as Open Library's User-Agent.
"""

import time

import httpx

from app.config import OPENALEX_API_KEY, OPENALEX_MAILTO

WORKS_URL = "https://api.openalex.org/works"

_CACHE_TTL_SECONDS = 300
_cache: dict[str, tuple[float, list[dict]]] = {}


async def search_scholarly_works(client: httpx.AsyncClient, query: str, limit: int = 5) -> list[dict]:
    """Search OpenAlex for scholarly works matching a topic or title.

    Returns a list of dicts: title, authors (comma-joined display names),
    year, citation_count, is_oa, doi, and abstract (reconstructed from
    OpenAlex's inverted-index representation, or None if unavailable).
    Results are cached in-process for a few minutes, matching
    `open_library_service`'s caching pattern.
    """
    cache_key = f"{query.strip().lower()}:{limit}"
    cached = _cache.get(cache_key)
    if cached and time.monotonic() - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]

    params = {"search": query, "per-page": limit}
    if OPENALEX_MAILTO:
        params["mailto"] = OPENALEX_MAILTO
    if OPENALEX_API_KEY:
        params["api_key"] = OPENALEX_API_KEY

    response = await client.get(WORKS_URL, params=params)
    response.raise_for_status()
    works = response.json().get("results", [])

    results = [
        {
            "title": work.get("title") or work.get("display_name") or "Untitled",
            "authors": ", ".join(
                a["author"]["display_name"] for a in work.get("authorships", []) if a.get("author")
            )
            or "Unknown author",
            "year": work.get("publication_year"),
            "citation_count": work.get("cited_by_count") or 0,
            "is_oa": bool((work.get("open_access") or {}).get("is_oa")),
            "doi": work.get("doi"),
            "abstract": _reconstruct_abstract(work.get("abstract_inverted_index")),
        }
        for work in works
    ]

    _cache[cache_key] = (time.monotonic(), results)
    return results


def _reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str | None:
    """OpenAlex ships abstracts as `{word: [position, ...]}` (to sidestep
    publisher copyright on the full text as contiguous prose) instead of
    plain text. Rebuild the plain-text abstract from word positions."""
    if not inverted_index:
        return None

    positions: dict[int, str] = {}
    for word, indices in inverted_index.items():
        for index in indices:
            positions[index] = word
    if not positions:
        return None
    return " ".join(positions[i] for i in sorted(positions))
