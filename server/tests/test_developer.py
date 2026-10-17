"""Tier 8 Phase 34: per-library API keys and the feedback webhook."""

import httpx
import pytest
from fastapi import HTTPException
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from app import api_keys, library_config, request_gate
from app.agent import chat_agent
from app.library_config import LibraryConfig
from app.routers import developer
from app.staff_auth import StaffMember


@pytest.fixture(autouse=True)
def fresh():
    api_keys.reset_cache()
    yield
    api_keys.reset_cache()


def test_keys_are_random_and_only_their_hash_is_kept():
    key, digest, prefix = api_keys.generate_key()
    other, _, _ = api_keys.generate_key()
    assert key.startswith("ls_") and key != other and len(key) > 40
    assert digest == api_keys.hash_key(key) and key not in digest
    assert key.startswith(prefix) and len(prefix) == 10


async def test_library_for_key_looks_up_the_hash_and_caches(monkeypatch):
    monkeypatch.setattr(library_config, "SUPABASE_URL", "https://p.supabase.co")
    monkeypatch.setattr(library_config, "SUPABASE_SECRET_KEY", "sb_secret_x")
    monkeypatch.setattr(api_keys, "SUPABASE_URL", "https://p.supabase.co")
    key, digest, _ = api_keys.generate_key()
    calls = []

    def handler(request: httpx.Request):
        calls.append(request)
        assert request.url.params["key_hash"] == f"eq.{digest}"
        assert request.url.params["revoked_at"] == "is.null"
        return httpx.Response(200, json=[{"library_id": "springfield-pl"}])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        assert await api_keys.library_for_key(client, key) == "springfield-pl"
        assert await api_keys.library_for_key(client, key) == "springfield-pl"
        assert await api_keys.library_for_key(client, "not-a-key") is None
    assert len(calls) == 1


def _echo(seen):
    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        seen.append(True)
        return ModelResponse(parts=[TextPart("ok")])

    return FunctionModel(respond)


def test_invalid_key_is_401(client, monkeypatch):
    async def none(client_, key):
        return None

    monkeypatch.setattr(request_gate, "library_for_key", none)
    assert client.post("/chat", json={"message": "hi"}, headers={"X-LibSync-Key": "ls_bad"}).status_code == 401


def test_valid_key_acts_for_its_library_without_browser_checks(client, monkeypatch):
    async def lib(client_, key):
        return "springfield-pl"

    async def config(client_, library_id):
        # An origin allowlist that a server-to-server call can't satisfy.
        return LibraryConfig(id=library_id, name="S", allowed_origins=frozenset({"https://springfield.example"}))

    monkeypatch.setattr(request_gate, "library_for_key", lib)
    monkeypatch.setattr(request_gate, "get_library_config", config)
    seen: list = []
    with chat_agent.override(model=_echo(seen)):
        response = client.post("/chat", json={"message": "hi"}, headers={"X-LibSync-Key": "ls_good"})
    assert response.status_code == 200 and seen


def test_key_cannot_use_an_assistant_the_library_switched_off(client, monkeypatch):
    async def lib(client_, key):
        return "springfield-pl"

    async def config(client_, library_id):
        return LibraryConfig(id=library_id, name="S", ai_enabled=False)

    monkeypatch.setattr(request_gate, "library_for_key", lib)
    monkeypatch.setattr(request_gate, "get_library_config", config)
    assert client.post("/chat", json={"message": "hi"}, headers={"X-LibSync-Key": "ls_good"}).status_code == 403


@pytest.fixture()
def rest_log(monkeypatch):
    log: list = []

    async def fake_rest(request, method, path, **kwargs):
        log.append((method, path, kwargs))
        return httpx.Response(200, json=[{"id": "k1", "name": "ILS", "prefix": "ls_abc1234"}])

    monkeypatch.setattr(developer, "_rest", fake_rest)
    return log


def _staff(monkeypatch, role="admin"):
    async def fake(request, library_id, admin=False):
        if admin and role != "admin":
            raise HTTPException(status_code=403, detail="admins only")
        return StaffMember(user_id="u1", email=None, role=role)

    monkeypatch.setattr(developer, "require_staff", fake)


def test_admin_creates_a_key_that_is_returned_once_and_stored_hashed(client, monkeypatch, rest_log):
    _staff(monkeypatch)
    body = client.post("/admin/libraries/springfield-pl/api-keys", json={"name": "Discovery layer"}).json()
    method, path, kwargs = rest_log[0]
    assert (method, path) == ("POST", "library_api_keys")
    stored = kwargs["json"]
    assert body["key"].startswith("ls_") and "key" not in stored
    assert stored["key_hash"] == api_keys.hash_key(body["key"])
    assert stored["library_id"] == "springfield-pl" and stored["created_by"] == "u1"


def test_only_admins_create_or_revoke_keys(client, monkeypatch, rest_log):
    _staff(monkeypatch, role="staff")
    assert client.post("/admin/libraries/springfield-pl/api-keys", json={"name": "x"}).status_code == 403
    assert client.delete("/admin/libraries/springfield-pl/api-keys/k1").status_code == 403
    assert client.get("/admin/libraries/springfield-pl/api-keys").status_code == 200  # staff may list


def test_revoke_sets_revoked_at(client, monkeypatch, rest_log):
    _staff(monkeypatch)
    assert client.delete("/admin/libraries/springfield-pl/api-keys/k1").json() == {"revoked": "k1"}
    method, path, kwargs = rest_log[0]
    assert method == "PATCH" and "revoked_at" in kwargs["json"]


def test_feedback_is_404_without_a_webhook(client, monkeypatch):
    async def config(client_, library_id):
        return LibraryConfig(id="springfield-pl", name="S")

    monkeypatch.setattr(developer, "get_library_config", config)
    response = client.post(
        "/feedback", json={"question": "q", "answer": "a"}, headers={"X-LibSync-Library": "springfield-pl"}
    )
    assert response.status_code == 404


def test_feedback_is_forwarded_to_the_librarys_webhook(client, monkeypatch):
    async def config(client_, library_id):
        return LibraryConfig(id="springfield-pl", name="S", feedback_webhook="https://hooks.springfield.example/x")

    posted: list[httpx.Request] = []

    def handler(request: httpx.Request):
        posted.append(request)
        return httpx.Response(200)

    monkeypatch.setattr(developer, "get_library_config", config)
    original = client.app.state.http_client
    client.app.state.http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        response = client.post(
            "/feedback",
            json={"question": "How late are you open?", "answer": "Until 8."},
            headers={"X-LibSync-Library": "springfield-pl"},
        )
    finally:
        client.app.state.http_client = original
    assert response.json() == {"sent": True}
    import json

    sent = json.loads(posted[0].content)
    assert str(posted[0].url) == "https://hooks.springfield.example/x"
    assert sent["question"] == "How late are you open?" and sent["type"] == "not_helpful"
