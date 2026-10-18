"""Tier 8 Phase 30: per-library settings from Supabase, and the guarantee that
the chat keeps working exactly as before when Supabase is off or failing."""

import httpx
import pytest
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from app import library_config, request_gate
from app.agent import chat_agent
from app.library_config import LibraryConfig, effective_tools, get_library_config


@pytest.fixture(autouse=True)
def fresh_cache():
    library_config.reset_cache()
    yield
    library_config.reset_cache()


@pytest.fixture()
def supabase_on(monkeypatch):
    monkeypatch.setattr(library_config, "SUPABASE_URL", "https://proj.supabase.co")
    monkeypatch.setattr(library_config, "SUPABASE_SECRET_KEY", "sb_secret_test")


ROW = {
    "id": "springfield-pl",
    "name": "Springfield Public Library",
    "help_url": "https://springfield.example/ask",
    "enabled_tools": ["policies", "catalog"],
    "ai_enabled": True,
    "allowed_origins": None,
    "catalog_driver": "openlibrary",
    "catalog_config": {},
}


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_returns_none_without_supabase():
    calls = []
    async with _client(lambda r: calls.append(r) or httpx.Response(200, json=[ROW])) as client:
        assert await get_library_config(client, "springfield-pl") is None
    assert calls == []


async def test_reads_and_caches_the_library_row(supabase_on):
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request):
        seen.append(request)
        return httpx.Response(200, json=[ROW])

    async with _client(handler) as client:
        first = await get_library_config(client, "springfield-pl")
        second = await get_library_config(client, "springfield-pl")
    assert first == second
    assert first.enabled_tools == frozenset({"policies", "catalog"})
    assert first.help_url == "https://springfield.example/ask"
    assert len(seen) == 1
    assert seen[0].url.params["id"] == "eq.springfield-pl"
    assert seen[0].headers["apikey"] == "sb_secret_test"
    assert "authorization" not in seen[0].headers  # new-style keys go in apikey only


@pytest.mark.parametrize("failure", [httpx.Response(500), httpx.ConnectError("down")])
async def test_fails_open_when_supabase_errors(supabase_on, failure):
    def handler(request):
        if isinstance(failure, Exception):
            raise failure
        return failure

    async with _client(handler) as client:
        assert await get_library_config(client, "springfield-pl") is None


async def test_unknown_library_is_none(supabase_on):
    async with _client(lambda r: httpx.Response(200, json=[])) as client:
        assert await get_library_config(client, "nobody") is None


def test_public_view_never_exposes_catalog_config():
    config = library_config._parse({**ROW, "catalog_config": {"base_url": "https://koha.example"}})
    # feedback_enabled is a yes/no flag; the webhook URL itself stays private.
    assert set(config.public()) == {
        "id", "name", "help_url", "enabled_tools", "ai_enabled", "feedback_enabled", "teach_search"
    }


@pytest.mark.parametrize(
    ("header", "configured", "expected"),
    [
        (None, None, None),
        (frozenset({"catalog"}), None, frozenset({"catalog"})),
        (None, frozenset({"policies"}), frozenset({"policies"})),
        (frozenset({"catalog", "policies"}), frozenset({"policies"}), frozenset({"policies"})),
    ],
)
def test_snippet_and_dashboard_can_only_narrow_tools(header, configured, expected):
    config = LibraryConfig(id="x", name="x", enabled_tools=configured) if configured is not None else None
    assert effective_tools(header, config) == expected


def _stub_config(monkeypatch, config):
    async def fake(client, library_id):
        return config if library_id == "springfield-pl" else None

    monkeypatch.setattr(request_gate, "get_library_config", fake)


def _echo_model(seen):
    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        seen.append({t.name for t in info.function_tools})
        return ModelResponse(parts=[TextPart("ok")])

    return FunctionModel(respond)


def test_dashboard_can_switch_the_assistant_off(client, monkeypatch):
    _stub_config(monkeypatch, LibraryConfig(id="springfield-pl", name="S", ai_enabled=False, help_url="tel:+15555550100"))
    response = client.post("/chat", json={"message": "hi"}, headers={"X-LibSync-Library": "springfield-pl"})
    assert response.status_code == 403
    assert response.json()["code"] == "ai_disabled"
    assert response.json()["help_url"] == "tel:+15555550100"


def test_dashboard_origin_allowlist(client, monkeypatch):
    _stub_config(
        monkeypatch,
        LibraryConfig(id="springfield-pl", name="S", allowed_origins=frozenset({"https://springfield.example"})),
    )
    seen: list[set[str]] = []
    headers = {"X-LibSync-Library": "springfield-pl"}
    with chat_agent.override(model=_echo_model(seen)):
        blocked = client.post("/chat", json={"message": "hi"}, headers={**headers, "Origin": "https://evil.example"})
        allowed = client.post(
            "/chat", json={"message": "hi"}, headers={**headers, "Origin": "https://springfield.example"}
        )
    assert blocked.status_code == 403
    assert allowed.status_code == 200


def test_dashboard_tools_apply_to_the_agent(client, monkeypatch):
    _stub_config(monkeypatch, LibraryConfig(id="springfield-pl", name="S", enabled_tools=frozenset({"citations"})))
    seen: list[set[str]] = []
    with chat_agent.override(model=_echo_model(seen)):
        response = client.post("/chat", json={"message": "hi"}, headers={"X-LibSync-Library": "springfield-pl"})
    assert response.status_code == 200
    assert seen == [{"lookup_and_cite"}]


def test_public_endpoint(client, monkeypatch):
    config = library_config._parse(ROW)

    async def fake(client_, library_id):
        return config if library_id == "springfield-pl" else None

    from app.routers import libraries

    monkeypatch.setattr(libraries, "get_library_config", fake)
    assert client.get("/libraries/springfield-pl").json()["name"] == "Springfield Public Library"
    assert client.get("/libraries/unknown").status_code == 404


def test_teach_search_defaults_off_and_reaches_the_patron_app():
    from app.library_config import _parse

    assert _parse({"id": "lib"}).public()["teach_search"] is False
    assert _parse({"id": "lib", "teach_search": True}).public()["teach_search"] is True
