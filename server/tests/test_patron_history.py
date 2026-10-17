"""Tier 9 Phase 37: synced history for signed-in patrons (Supabase mocked)."""

import httpx
import pytest

from app import patron_auth
from app.routers import patron_history


@pytest.fixture()
def store(monkeypatch):
    monkeypatch.setattr(patron_auth, "PATRON_SESSION_SECRET", "secret")
    monkeypatch.setattr(patron_history, "supabase_enabled", lambda: True)
    rows: list[dict] = []
    calls: list[tuple] = []

    def mine(params, row):
        return params.get("patron_ref") == f"eq.{row['patron_ref']}" and params.get("library_id") == f"eq.{row['library_id']}"

    async def fake_rest(request, method, **kwargs):
        params = kwargs.get("params", {})
        calls.append((method, params, kwargs.get("json")))
        if method == "GET":
            return httpx.Response(200, json=[r for r in rows if mine(params, r)])
        if method == "POST":
            body = kwargs["json"]
            rows[:] = [r for r in rows if not (r["patron_ref"] == body["patron_ref"] and r["id"] == body["id"])]
            rows.append(body)
        if method == "DELETE":
            keep = []
            for r in rows:
                matches = mine(params, r) and ("id" not in params or params["id"] == f"eq.{r['id']}")
                if "updated_at" in params:
                    matches = False  # nothing is old enough in these tests
                if not matches:
                    keep.append(r)
            rows[:] = keep
        return httpx.Response(204)

    monkeypatch.setattr(patron_history, "_rest", fake_rest)
    return {"rows": rows, "calls": calls}


def _token(library="springfield-pl", identity="card-1"):
    token, _ = patron_auth.issue(library, "card", identity, card=identity)
    return {"X-LibSync-Patron": token}


CONVERSATION = {"title": "Late fees", "createdAt": 1, "updatedAt": 2, "entries": [{"kind": "user", "id": "u1", "text": "hi"}]}


def test_requires_a_session(client, store):
    assert client.get("/patron/conversations").status_code == 401


def test_save_then_list_round_trips(client, store):
    headers = _token()
    assert client.put("/patron/conversations/c1", json=CONVERSATION, headers=headers).status_code == 200
    listed = client.get("/patron/conversations", headers=headers).json()
    assert listed == [{"id": "c1", **CONVERSATION}]
    saved = store["rows"][0]
    assert saved["patron_ref"] == patron_auth.patron_ref("springfield-pl", "card-1")
    assert "card-1" not in str(saved)  # stored by one-way reference, never the card number


def test_patrons_only_see_their_own_history(client, store):
    client.put("/patron/conversations/c1", json=CONVERSATION, headers=_token(identity="alice"))
    assert client.get("/patron/conversations", headers=_token(identity="bob")).json() == []
    assert client.get("/patron/conversations", headers=_token(library="other", identity="alice")).json() == []


def test_list_purges_expired_history_first(client, store):
    client.get("/patron/conversations", headers=_token())
    method, params, _ = store["calls"][0]
    assert method == "DELETE" and params["updated_at"].startswith("lt.")


def test_delete_one_and_all(client, store):
    headers = _token()
    for cid in ("c1", "c2"):
        client.put(f"/patron/conversations/{cid}", json=CONVERSATION, headers=headers)
    client.delete("/patron/conversations/c1", headers=headers)
    assert [r["id"] for r in store["rows"]] == ["c2"]
    client.delete("/patron/conversations", headers=headers)
    assert store["rows"] == []


def test_oversized_and_too_many_conversations_are_refused(client, store, monkeypatch):
    headers = _token()
    big = {**CONVERSATION, "entries": [{"text": "x" * 300_000}]}
    assert client.put("/patron/conversations/c1", json=big, headers=headers).status_code == 413
    monkeypatch.setattr(patron_history, "MAX_CONVERSATIONS", 1)
    client.put("/patron/conversations/c1", json=CONVERSATION, headers=headers)
    assert client.put("/patron/conversations/c2", json=CONVERSATION, headers=headers).status_code == 409
    assert client.put("/patron/conversations/c1", json=CONVERSATION, headers=headers).status_code == 200  # updates still fine


def test_unavailable_without_supabase(client, monkeypatch):
    monkeypatch.setattr(patron_auth, "PATRON_SESSION_SECRET", "secret")
    monkeypatch.setattr(patron_history, "supabase_enabled", lambda: False)
    assert client.get("/patron/conversations", headers=_token()).status_code == 404
