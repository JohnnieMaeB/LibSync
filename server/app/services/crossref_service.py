"""Client for the Crossref REST API — free, keyless.

See https://api.crossref.org/. A `mailto=` param puts requests in the
"polite pool" for higher, more reliable rate limits, matching the courtesy
pattern used by `open_library_service` and `openalex_service`.
"""

import time

import httpx

from app.config import CROSSREF_MAILTO

WORK_BY_DOI_URL = "https://api.crossref.org/works/{doi}"
WORKS_SEARCH_URL = "https://api.crossref.org/works"

# Keyed by DOI (lowercased) or "title:<query>". Lets a citation style switch
# (see the /citation/{doi} route in routers/agent.py) re-run only the
# citeproc formatting step for a DOI already resolved this turn, instead of
# hitting Crossref again for every style the patron clicks through.
_CACHE_TTL_SECONDS = 300
_cache: dict[str, tuple[float, dict | None]] = {}


async def lookup_work(client: httpx.AsyncClient, *, doi: str | None = None, title: str | None = None) -> dict | None:
    """Resolve a Crossref bibliographic record by DOI (exact) or free-text
    title/author search (best match, first result).

    Returns the raw Crossref work object (title, author, container-title,
    volume, issue, page, publisher, issued, DOI, type) — real bibliographic
    fields, not recalled from a model's memory — or `None` if nothing was
    found.

    Raises:
        ValueError: If neither `doi` nor `title` is given.
    """
    if not doi and not title:
        raise ValueError("Either doi or title is required.")

    cache_key = f"doi:{doi.strip().lower()}" if doi else f"title:{title.strip().lower()}"
    cached = _cache.get(cache_key)
    if cached and time.monotonic() - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]

    params = {"mailto": CROSSREF_MAILTO} if CROSSREF_MAILTO else {}

    if doi:
        response = await client.get(WORK_BY_DOI_URL.format(doi=doi), params=params)
        if response.status_code == 404:
            work = None
        else:
            response.raise_for_status()
            work = response.json()["message"]
    else:
        response = await client.get(WORKS_SEARCH_URL, params={**params, "query.bibliographic": title, "rows": 1})
        response.raise_for_status()
        items = response.json()["message"]["items"]
        work = items[0] if items else None

    _cache[cache_key] = (time.monotonic(), work)
    return work
