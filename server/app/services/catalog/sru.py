"""SRU (Search/Retrieve via URL) catalog driver: a best-effort, cross-ILS
fallback. Documented for Koha (its Zebra server) and Alma; live-tested against
the Library of Congress's public SRU server.

catalog_config:
  base_url        SRU endpoint, e.g. https://library.example:9999/biblios
  version         SRU version (default 1.1)
  query_template  CQL with {q}; default '"{q}"' (the server's default index)
  record_url      optional link template with {id}, {lccn} or {isbn}
  items_tag       "952" for a Koha (Zebra) SRU server, to read item availability;
                  leave unset elsewhere (other catalogs use 952 for other data)
"""

import xml.etree.ElementTree as ET

import httpx

from app.services.catalog.marc import MARC_NS, parse_records


def _cql_escape(query: str) -> str:
    return query.replace("\\", "\\\\").replace('"', '\\"')


async def search(client: httpx.AsyncClient, settings: dict, query: str, limit: int) -> list[dict]:
    base_url = settings.get("base_url")
    if not base_url:
        raise ValueError("SRU driver needs catalog_config.base_url")
    cql = settings.get("query_template", '"{q}"').format(q=_cql_escape(query.strip()))
    response = await client.get(
        base_url,
        params={
            "version": settings.get("version", "1.1"),
            "operation": "searchRetrieve",
            "query": cql,
            "maximumRecords": str(limit),
            "recordSchema": "marcxml",
        },
        timeout=10.0,
    )
    response.raise_for_status()
    root = ET.fromstring(response.content)
    records = root.findall(f".//{MARC_NS}record")
    return parse_records(records, settings.get("record_url"), settings.get("items_tag"))[:limit]
