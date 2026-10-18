"""Koha REST API catalog driver (the first vendor driver; TIER8_PLAN.md §2.4).

Authenticates with OAuth2 client credentials (Koha: Administration → System
preferences → RESTOAuth2ClientCredentials, then a patron's "Manage API keys"),
searches bibliographic records, and checks item availability.

Written to Koha's documented REST API (/api/v1/oauth/token, GET
/api/v1/biblios with a `q` query, GET /api/v1/biblios/{id}/items), covered
by mocked tests, and run weekly against a real Koha (koha-testing-docker;
.github/workflows/koha-live.yml).

catalog_config:
  base_url    Koha staff REST base, e.g. https://staff.library.example
  client_id   OAuth client id (the secret is library_secrets.koha_client_secret)
  opac_url    optional OPAC base for link-outs, e.g. https://catalog.library.example
"""

import json
import time

import httpx

_token_cache: dict[str, tuple[float, str]] = {}


async def _token(client: httpx.AsyncClient, base_url: str, client_id: str, client_secret: str) -> str:
    key = f"{base_url}|{client_id}"
    cached = _token_cache.get(key)
    if cached and cached[0] > time.monotonic():
        return cached[1]
    response = await client.post(
        f"{base_url}/api/v1/oauth/token",
        data={"grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret},
        timeout=10.0,
    )
    response.raise_for_status()
    body = response.json()
    # Refresh a minute early so a token never expires mid-search.
    _token_cache[key] = (time.monotonic() + max(int(body.get("expires_in", 3600)) - 60, 0), body["access_token"])
    return body["access_token"]


def _availability(items: list[dict]) -> str:
    if not items:
        return "in catalog"
    for item in items:
        checked_out = item.get("checked_out_date") or item.get("checkout")
        unavailable = item.get("not_for_loan_status") or item.get("lost_status") or item.get("withdrawn")
        if not checked_out and not unavailable:
            return "available"
    return "checked out"


async def search(
    client: httpx.AsyncClient, settings: dict, client_secret: str | None, query: str, limit: int
) -> list[dict]:
    base_url = (settings.get("base_url") or "").rstrip("/")
    client_id = settings.get("client_id")
    if not base_url or not client_id or not client_secret:
        raise ValueError("Koha driver needs catalog_config.base_url, client_id and the koha_client_secret secret")
    headers = {"Authorization": f"Bearer {await _token(client, base_url, client_id, client_secret)}", "Accept": "application/json"}
    term = f"%{query.strip()}%"
    q = json.dumps({"-or": [{"title": {"-like": term}}, {"author": {"-like": term}}]})
    response = await client.get(
        f"{base_url}/api/v1/biblios", params={"q": q, "_per_page": str(limit)}, headers=headers, timeout=10.0
    )
    response.raise_for_status()
    opac_url = (settings.get("opac_url") or "").rstrip("/")

    books = []
    for biblio in response.json()[:limit]:
        biblio_id = biblio.get("biblio_id")
        items_response = await client.get(f"{base_url}/api/v1/biblios/{biblio_id}/items", headers=headers, timeout=10.0)
        items = items_response.json() if items_response.status_code == 200 else []
        year = str(biblio.get("copyright_date") or biblio.get("publication_year") or "")[:4]
        books.append(
            {
                "title": (biblio.get("title") or "Untitled").strip(" /:"),
                "author": biblio.get("author") or "Unknown author",
                "first_publish_year": int(year) if year.isdigit() else None,
                "cover_url": None,
                "url": f"{opac_url}/cgi-bin/koha/opac-detail.pl?biblionumber={biblio_id}" if opac_url else None,
                "availability": _availability(items),
            }
        )
    return books
