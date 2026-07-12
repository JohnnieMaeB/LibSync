import httpx
import pytest

from app.services import crossref_service


@pytest.fixture(autouse=True)
def clear_cache():
    crossref_service._cache.clear()
    yield
    crossref_service._cache.clear()


def _make_client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


_SAMPLE_MESSAGE = {
    "DOI": "10.1016/j.lindif.2023.102274",
    "type": "journal-article",
    "title": ["ChatGPT for good?"],
    "author": [{"given": "Enkelejda", "family": "Kasneci"}],
    "container-title": ["Learning and Individual Differences"],
    "volume": "103",
    "page": "102274",
    "publisher": "Elsevier BV",
    "issued": {"date-parts": [[2023, 4]]},
}


async def test_lookup_work_by_doi_returns_the_message():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "works/10.1016%2Fj.lindif.2023.102274" in str(request.url) or "10.1016" in str(request.url)
        return httpx.Response(200, json={"message": _SAMPLE_MESSAGE})

    client = _make_client(handler)
    try:
        work = await crossref_service.lookup_work(client, doi="10.1016/j.lindif.2023.102274")
    finally:
        await client.aclose()

    assert work["DOI"] == "10.1016/j.lindif.2023.102274"
    assert work["title"] == ["ChatGPT for good?"]


async def test_lookup_work_by_doi_returns_none_on_404():
    client = _make_client(lambda request: httpx.Response(404))
    try:
        work = await crossref_service.lookup_work(client, doi="10.0000/does-not-exist")
    finally:
        await client.aclose()

    assert work is None


async def test_lookup_work_by_title_returns_first_search_result():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "query.bibliographic" in str(request.url)
        return httpx.Response(200, json={"message": {"items": [_SAMPLE_MESSAGE]}})

    client = _make_client(handler)
    try:
        work = await crossref_service.lookup_work(client, title="ChatGPT for good education")
    finally:
        await client.aclose()

    assert work["DOI"] == "10.1016/j.lindif.2023.102274"


async def test_lookup_work_by_title_returns_none_for_no_matches():
    client = _make_client(lambda request: httpx.Response(200, json={"message": {"items": []}}))
    try:
        work = await crossref_service.lookup_work(client, title="asdkjfhaslkdjfh")
    finally:
        await client.aclose()

    assert work is None


async def test_lookup_work_requires_doi_or_title():
    client = _make_client(lambda request: httpx.Response(200, json={}))
    try:
        with pytest.raises(ValueError):
            await crossref_service.lookup_work(client)
    finally:
        await client.aclose()


async def test_lookup_work_caches_repeated_doi_lookups():
    request_log: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        request_log.append(str(request.url))
        return httpx.Response(200, json={"message": _SAMPLE_MESSAGE})

    client = _make_client(handler)
    try:
        await crossref_service.lookup_work(client, doi="10.1016/j.lindif.2023.102274")
        first_call_count = len(request_log)
        await crossref_service.lookup_work(client, doi="10.1016/j.lindif.2023.102274")
    finally:
        await client.aclose()

    assert len(request_log) == first_call_count


async def test_lookup_work_sends_mailto(monkeypatch):
    monkeypatch.setattr(crossref_service, "CROSSREF_MAILTO", "libsync@example.com")
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["params"] = dict(request.url.params)
        return httpx.Response(200, json={"message": _SAMPLE_MESSAGE})

    client = _make_client(handler)
    try:
        await crossref_service.lookup_work(client, doi="10.1016/j.lindif.2023.102274")
    finally:
        await client.aclose()

    assert captured["params"]["mailto"] == "libsync@example.com"
