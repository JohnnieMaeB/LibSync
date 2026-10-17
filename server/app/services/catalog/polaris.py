"""Polaris API (PAPI) catalog driver (the second vendor driver; TIER8_PLAN.md
§2.4). Uses PAPI's public keyword bibliographic search, signed with the
library's PAPI access id and key (HMAC-SHA1 over method, URI and date, sent as
`Authorization: PWS id:signature`).

**Not yet verified against a live Polaris server**: written to Innovative's
PAPI reference (public `search/bibs/keyword/KW`) and covered by mocked tests.
Verify against a Polaris Developer Network sandbox before relying on it.

catalog_config:
  base_url    PAPI service base, e.g. https://papi.library.example/PAPIService/REST
  access_id   PAPI access id (the key is library_secrets.polaris_access_key)
  org_id      organization id to search (default 1, the whole system)
  lang_id     default 1033 (English)
  app_id      default 100, PAPI's documented value for customers and third parties
  pac_url     optional PowerPAC base for link-outs
"""

import base64
import hashlib
import hmac
from email.utils import formatdate
from urllib.parse import quote

import httpx


def signature(access_key: str, method: str, uri: str, date: str) -> str:
    digest = hmac.new(access_key.encode(), f"{method}{uri}{date}".encode(), hashlib.sha1).digest()
    return base64.b64encode(digest).decode()


def _availability(row: dict) -> str:
    in_count = row.get("LocalItemsIn", row.get("SystemItemsIn"))
    total = row.get("LocalItemsTotal", row.get("SystemItemsTotal"))
    if in_count is None:
        return "in catalog"
    if in_count > 0:
        return "available"
    return "checked out" if total else "in catalog"


async def search(
    client: httpx.AsyncClient, settings: dict, access_key: str | None, query: str, limit: int
) -> list[dict]:
    base_url = (settings.get("base_url") or "").rstrip("/")
    access_id = settings.get("access_id")
    if not base_url or not access_id or not access_key:
        raise ValueError("Polaris driver needs catalog_config.base_url, access_id and the polaris_access_key secret")
    lang_id = settings.get("lang_id", 1033)
    app_id = settings.get("app_id", 100)
    org_id = settings.get("org_id", 1)
    uri = (
        f"{base_url}/public/v1/{lang_id}/{app_id}/{org_id}/search/bibs/keyword/KW"
        f"?q={quote(query.strip())}&bibsperpage={limit}"
    )
    date = formatdate(usegmt=True)
    response = await client.get(
        uri,
        headers={
            "Authorization": f"PWS {access_id}:{signature(access_key, 'GET', uri, date)}",
            "PolarisDate": date,
            "Accept": "application/json",
        },
        timeout=10.0,
    )
    response.raise_for_status()
    body = response.json()
    if body.get("PAPIErrorCode", 0) < 0:
        raise RuntimeError(f"PAPI error {body['PAPIErrorCode']}: {body.get('ErrorMessage')}")

    pac_url = (settings.get("pac_url") or "").rstrip("/")
    books = []
    for row in (body.get("BibSearchRows") or [])[:limit]:
        year = str(row.get("PublicationDate") or "")[:4]
        isbn = (row.get("ISBN") or "").split(" ")[0]
        control = row.get("ControlNumber")
        books.append(
            {
                "title": (row.get("Title") or "Untitled").strip(" /:"),
                "author": row.get("Author") or "Unknown author",
                "first_publish_year": int(year) if year.isdigit() else None,
                "cover_url": f"https://covers.openlibrary.org/b/isbn/{isbn}-M.jpg?default=false" if isbn else None,
                "url": f"{pac_url}/search/title.aspx?pos=1&cn={control}" if pac_url and control else None,
                "availability": _availability(row),
            }
        )
    return books
