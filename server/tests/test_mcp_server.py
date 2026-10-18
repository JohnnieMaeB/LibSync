"""The MCP endpoint (app/mcp_server.py): LibSync's grounded lookups as Model
Context Protocol tools at /mcp, over plain JSON-RPC."""

import json

import pytest

from app import mcp_server
from app.library_config import LibraryConfig
from app.services import catalog
from app.services.catalog import CatalogSearch

HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
BOOK = {"title": "Beloved", "author": "Toni Morrison", "first_publish_year": 1987, "cover_url": None, "url": None,
        "availability": "available"}


def _rpc(client, method: str, params: dict | None = None, headers: dict | None = None):
    body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
    return client.post("/mcp/", content=json.dumps(body), headers={**HEADERS, **(headers or {})})


def _tool_result(response) -> dict:
    result = response.json()["result"]
    return result.get("structuredContent") or json.loads(result["content"][0]["text"])


def test_lists_the_grounded_tools(client):
    response = _rpc(client, "tools/list")
    names = {tool["name"] for tool in response.json()["result"]["tools"]}
    assert names == {"search_library_policies", "search_catalog", "recommend_books", "search_scholarly_works", "cite"}


def test_a_tool_call_returns_the_catalogs_own_data(client, monkeypatch):
    async def search(http, config, query, limit=3):
        assert config is None and query == "Beloved"  # no key: the demo library
        return CatalogSearch([BOOK], "Open Library")

    monkeypatch.setattr(catalog, "search_catalog", search)
    response = _rpc(client, "tools/call", {"name": "search_catalog", "arguments": {"query": "Beloved"}})
    assert _tool_result(response) == {"source": "Open Library", "fell_back": False, "books": [BOOK]}


def test_an_api_key_applies_that_librarys_switches(client, monkeypatch):
    async def library_for_key(http, key):
        return "springfield" if key == "lsk_test" else None

    async def get_config(http, library_id):
        return LibraryConfig(id=library_id, name="Springfield", enabled_tools=frozenset({"policies"}))

    monkeypatch.setattr(mcp_server, "library_for_key", library_for_key)
    monkeypatch.setattr(mcp_server, "get_library_config", get_config)
    response = _rpc(
        client, "tools/call", {"name": "search_catalog", "arguments": {"query": "x"}}, headers={"X-LibSync-Key": "lsk_test"}
    )
    assert "switched off catalog" in _tool_result(response)["error"]


def test_a_library_that_turned_its_assistant_off_is_off_here_too(client, monkeypatch):
    async def library_for_key(http, key):
        return "springfield"

    async def get_config(http, library_id):
        return LibraryConfig(id=library_id, name="Springfield", ai_enabled=False)

    monkeypatch.setattr(mcp_server, "library_for_key", library_for_key)
    monkeypatch.setattr(mcp_server, "get_library_config", get_config)
    response = _rpc(
        client, "tools/call", {"name": "cite", "arguments": {"doi": "10.1/x"}}, headers={"X-LibSync-Key": "lsk_x"}
    )
    assert "error" in _tool_result(response)


async def test_the_rate_limit_answers_429():
    sent = []

    async def app(scope, receive, send):
        sent.append("app")

    async def send(message):
        if message["type"] == "http.response.start":
            sent.append(message["status"])

    limited = mcp_server.RateLimit(app, per_minute=2)
    scope = {"type": "http", "method": "POST", "client": ("1.2.3.4", 1), "headers": []}
    for _ in range(3):
        await limited(scope, None, send)
    assert sent == ["app", "app", 429]


def test_the_bare_path_is_served_without_a_redirect(client):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
    response = client.post("/mcp", content=body, headers=HEADERS, follow_redirects=False)
    assert response.status_code == 200 and response.json()["result"]["tools"]
