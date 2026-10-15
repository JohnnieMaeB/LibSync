"""Catalog connectors — Tier 8 Phase 32 (TIER8_PLAN.md §2.4).

One driver per ILS API, the model Aspen Discovery uses across Koha, Evergreen,
Polaris, Sierra and Symphony. Every driver returns the same book dicts the
Open Library service always has (title, author, first_publish_year,
cover_url, url, availability), so the book card and the agent don't change.

A library picks its driver in the dashboard (`libraries.catalog_driver` +
non-secret `catalog_config`; credentials in `library_secrets`). Anything
missing, misconfigured or failing falls back to Open Library, labeled as
such, so catalog search never goes down because a library's ILS did.
"""

from dataclasses import dataclass

import httpx

from app.library_config import LibraryConfig, get_library_secret
from app.services import open_library_service
from app.services.catalog import koha, polaris, sru

DRIVERS = ("openlibrary", "koha", "polaris", "sru")


@dataclass(frozen=True)
class CatalogSearch:
    results: list[dict]
    source: str  # who answered, for the agent's reply ("Open Library", "the library's catalog")
    fell_back: bool = False


async def _library_search(client: httpx.AsyncClient, config: LibraryConfig, query: str, limit: int) -> list[dict]:
    settings = config.catalog_config or {}
    driver = config.catalog_driver
    if driver == "sru":
        return await sru.search(client, settings, query, limit)
    if driver == "koha":
        secret = await get_library_secret(client, config.id, "koha_client_secret")
        return await koha.search(client, settings, secret, query, limit)
    if driver == "polaris":
        secret = await get_library_secret(client, config.id, "polaris_access_key")
        return await polaris.search(client, settings, secret, query, limit)
    raise ValueError(f"Unknown catalog driver {driver!r}")


async def search_catalog(
    client: httpx.AsyncClient, config: LibraryConfig | None, query: str, limit: int = 3
) -> CatalogSearch:
    if config is not None and config.catalog_driver != "openlibrary":
        try:
            return CatalogSearch(await _library_search(client, config, query, limit), "the library's catalog")
        except Exception as error:
            print(f"Catalog driver {config.catalog_driver!r} failed for {config.id}, using Open Library:", error)
            results = await open_library_service.search_catalog(client, query, limit=limit)
            return CatalogSearch(results, "Open Library", fell_back=True)
    return CatalogSearch(await open_library_service.search_catalog(client, query, limit=limit), "Open Library")
