"""Tier 8 Phase 37T part 2: LibAnswers FAQ sync (LibAnswers mocked)."""

import httpx
import pytest

from app.library_config import LibraryConfig
from app.routers import faq_sync
from app.services import libanswers
from app.staff_auth import StaffMember


def _faq_page(n: int, start: int = 0):
    return [{"question": f"<p>Question {i}?</p>", "answer": f"<b>Answer</b> {i}.", "url": f"https://x/faq/{i}"} for i in range(start, start + n)]


async def test_fetch_pages_and_strips_html():
    pages = {"1": _faq_page(100), "2": _faq_page(3, start=100)}

    def handler(request: httpx.Request):
        if request.url.path == "/api/1.1/oauth/token":
            return httpx.Response(200, json={"access_token": "tok"})
        assert request.headers["authorization"] == "Bearer tok"
        assert request.url.params["iid"] == "42"
        return httpx.Response(200, json=pages[request.url.params["page"]])

    settings = {"site": "lib.libanswers.com", "iid": "42", "client_id": "cid"}
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        faqs = await libanswers.fetch_faqs(client, settings, "sec")
    assert len(faqs) == 103
    assert faqs[0] == {"question": "Question 0?", "answer": "Answer 0.", "url": "https://x/faq/0"}


async def test_fetch_accepts_a_wrapped_response_shape():
    def handler(request: httpx.Request):
        if request.url.path.endswith("/oauth/token"):
            return httpx.Response(200, json={"access_token": "tok"})
        return httpx.Response(200, json={"data": {"faqs": _faq_page(2)}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        faqs = await libanswers.fetch_faqs(client, {"site": "lib.libanswers.com", "client_id": "c"}, "s")
    assert len(faqs) == 2


def test_each_faq_is_one_chunk_with_question_and_answer():
    assert libanswers.faq_chunks([{"question": "Q1?", "answer": "A1."}]) == ["Q: Q1?\nA: A1."]


@pytest.fixture()
def staff(monkeypatch):
    async def fake_staff(request, library_id, admin=False):
        return StaffMember(user_id="u", email=None, role="staff")

    monkeypatch.setattr(faq_sync, "require_staff", fake_staff)


def _config(monkeypatch, config):
    async def fake(client, library_id):
        return config

    monkeypatch.setattr(faq_sync, "get_library_config", fake)


def test_sync_requires_libanswers_to_be_connected(client, staff, monkeypatch):
    _config(monkeypatch, LibraryConfig(id="springfield-pl", name="S"))
    assert client.post("/admin/libraries/springfield-pl/faq-sync").status_code == 409


def test_sync_indexes_faqs_as_one_document(client, staff, monkeypatch):
    _config(monkeypatch, LibraryConfig(id="springfield-pl", name="S", integrations={"libanswers": {"site": "x", "client_id": "c"}}))
    indexed = {}

    async def fake_secret(client_, library_id, name):
        return "sec"

    async def fake_fetch(client_, settings, secret):
        return [{"question": "Q?", "answer": "A.", "url": None}]

    async def fake_index(request, library_id, name, chunks, user_id):
        indexed.update(library_id=library_id, name=name, chunks=chunks)
        return {"id": "d1", "name": name, "chunk_count": len(chunks)}

    monkeypatch.setattr(faq_sync, "get_library_secret", fake_secret)
    monkeypatch.setattr(faq_sync.libanswers, "fetch_faqs", fake_fetch)
    monkeypatch.setattr(faq_sync, "index_document", fake_index)
    response = client.post("/admin/libraries/springfield-pl/faq-sync")
    assert response.json() == {"id": "d1", "name": "LibAnswers FAQs", "chunk_count": 1, "faq_count": 1}
    assert indexed == {"library_id": "springfield-pl", "name": "LibAnswers FAQs", "chunks": ["Q: Q?\nA: A."]}


def test_sync_reports_libanswers_outages_without_changes(client, staff, monkeypatch):
    _config(monkeypatch, LibraryConfig(id="springfield-pl", name="S", integrations={"libanswers": {"site": "x", "client_id": "c"}}))

    async def fake_secret(client_, library_id, name):
        return "sec"

    async def failing_fetch(client_, settings, secret):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(faq_sync, "get_library_secret", fake_secret)
    monkeypatch.setattr(faq_sync.libanswers, "fetch_faqs", failing_fetch)
    assert client.post("/admin/libraries/springfield-pl/faq-sync").status_code == 502
