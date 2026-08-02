import httpx
import pytest

from app.services import openalex_service


@pytest.fixture(autouse=True)
def clear_cache():
    openalex_service._cache.clear()
    yield
    openalex_service._cache.clear()


def _make_client(handler, request_log: list[str] | None = None) -> httpx.AsyncClient:
    def wrapped(request: httpx.Request) -> httpx.Response:
        if request_log is not None:
            request_log.append(str(request.url))
        return handler(request)

    return httpx.AsyncClient(transport=httpx.MockTransport(wrapped))


_SAMPLE_WORK = {
    "id": "https://openalex.org/W4323655724",
    "doi": "https://doi.org/10.1016/j.lindif.2023.102274",
    "title": "ChatGPT for good?",
    "display_name": "ChatGPT for good?",
    "publication_year": 2023,
    "cited_by_count": 5340,
    "open_access": {"is_oa": True, "oa_status": "green"},
    "authorships": [
        {"author": {"id": "https://openalex.org/A1", "display_name": "Enkelejda Kasneci"}},
        {"author": {"id": "https://openalex.org/A2", "display_name": "Kathrin Sessler"}},
    ],
    "abstract_inverted_index": {"Large": [0], "language": [1], "models": [2], "help.": [3]},
}


def _search_handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"results": [_SAMPLE_WORK]})


async def test_search_scholarly_works_returns_title_authors_year_and_oa():
    client = _make_client(_search_handler)
    try:
        results = await openalex_service.search_scholarly_works(client, "large language models")
    finally:
        await client.aclose()

    assert len(results) == 1
    work = results[0]
    assert work["title"] == "ChatGPT for good?"
    assert work["authors"] == "Enkelejda Kasneci, Kathrin Sessler"
    assert work["year"] == 2023
    assert work["citation_count"] == 5340
    assert work["is_oa"] is True
    assert work["doi"] == "https://doi.org/10.1016/j.lindif.2023.102274"
    assert work["abstract"] == "Large language models help."


async def test_search_scholarly_works_returns_empty_list_for_no_matches():
    client = _make_client(lambda request: httpx.Response(200, json={"results": []}))
    try:
        results = await openalex_service.search_scholarly_works(client, "asdkjfhaslkdjfh")
    finally:
        await client.aclose()

    assert results == []


async def test_search_scholarly_works_handles_missing_abstract_and_authors():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "title": "A Lonely Paper",
                        "publication_year": None,
                        "cited_by_count": 0,
                        "open_access": {"is_oa": False},
                        "authorships": [],
                    }
                ]
            },
        )

    client = _make_client(handler)
    try:
        results = await openalex_service.search_scholarly_works(client, "lonely")
    finally:
        await client.aclose()

    work = results[0]
    assert work["authors"] == "Unknown author"
    assert work["abstract"] is None
    assert work["is_oa"] is False


async def test_search_scholarly_works_caches_repeated_queries():
    request_log: list[str] = []
    client = _make_client(_search_handler, request_log)
    try:
        await openalex_service.search_scholarly_works(client, "large language models")
        first_call_count = len(request_log)
        await openalex_service.search_scholarly_works(client, "large language models")
    finally:
        await client.aclose()

    assert len(request_log) == first_call_count


async def test_search_scholarly_works_sends_mailto_and_api_key(monkeypatch):
    monkeypatch.setattr(openalex_service, "OPENALEX_MAILTO", "libsync@example.com")
    monkeypatch.setattr(openalex_service, "OPENALEX_API_KEY", "test-key")

    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["params"] = dict(request.url.params)
        return httpx.Response(200, json={"results": []})

    client = _make_client(handler)
    try:
        await openalex_service.search_scholarly_works(client, "test query")
    finally:
        await client.aclose()

    assert captured["params"]["mailto"] == "libsync@example.com"
    assert captured["params"]["api_key"] == "test-key"
