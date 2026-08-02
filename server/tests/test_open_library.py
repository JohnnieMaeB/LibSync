import httpx
import pytest

from app.services import open_library_service


@pytest.fixture(autouse=True)
def clear_cache():
    open_library_service._cache.clear()
    yield
    open_library_service._cache.clear()


def _make_client(handler, request_log: list[str] | None = None) -> httpx.AsyncClient:
    def wrapped(request: httpx.Request) -> httpx.Response:
        if request_log is not None:
            request_log.append(str(request.url))
        return handler(request)

    return httpx.AsyncClient(transport=httpx.MockTransport(wrapped))


def _search_handler(request: httpx.Request) -> httpx.Response:
    if "search.json" in str(request.url):
        return httpx.Response(
            200,
            json={
                "docs": [
                    {
                        "title": "Project Hail Mary",
                        "author_name": ["Andy Weir"],
                        "first_publish_year": 2021,
                        "cover_i": 12345,
                        "key": "/works/OL123W",
                        "edition_key": ["OL456M"],
                        "ebook_access": "borrowable",
                    }
                ]
            },
        )
    if "volumes/brief" in str(request.url):
        return httpx.Response(200, json={"items": [{"status": "lendable"}]})
    return httpx.Response(404)


async def test_search_catalog_returns_title_author_and_availability():
    client = _make_client(_search_handler)
    try:
        results = await open_library_service.search_catalog(client, "Project Hail Mary")
    finally:
        await client.aclose()

    assert len(results) == 1
    book = results[0]
    assert book["title"] == "Project Hail Mary"
    assert book["author"] == "Andy Weir"
    assert book["first_publish_year"] == 2021
    assert book["availability"] == "lendable"
    assert book["cover_url"] == "https://covers.openlibrary.org/b/id/12345-M.jpg"
    assert book["url"] == "https://openlibrary.org/works/OL123W"


async def test_search_catalog_falls_back_to_ebook_access_without_edition():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"docs": [{"title": "No Edition Book", "author_name": ["Someone"], "ebook_access": "public"}]},
        )

    client = _make_client(handler)
    try:
        results = await open_library_service.search_catalog(client, "No Edition Book")
    finally:
        await client.aclose()

    assert results[0]["availability"] == "public"
    assert results[0]["cover_url"] is None
    assert results[0]["url"] is None


async def test_search_catalog_returns_empty_list_for_no_matches():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"docs": []})

    client = _make_client(handler)
    try:
        results = await open_library_service.search_catalog(client, "asdkjfhaslkdjfh")
    finally:
        await client.aclose()

    assert results == []


async def test_search_catalog_caches_repeated_queries():
    request_log: list[str] = []
    client = _make_client(_search_handler, request_log)
    try:
        await open_library_service.search_catalog(client, "Project Hail Mary")
        first_call_count = len(request_log)
        await open_library_service.search_catalog(client, "Project Hail Mary")
    finally:
        await client.aclose()

    assert len(request_log) == first_call_count


async def test_availability_check_defaults_to_unknown_on_error():
    def handler(request: httpx.Request) -> httpx.Response:
        if "search.json" in str(request.url):
            return httpx.Response(
                200,
                json={"docs": [{"title": "Flaky Book", "author_name": ["Author"], "edition_key": ["OL999M"]}]},
            )
        return httpx.Response(500)

    client = _make_client(handler)
    try:
        results = await open_library_service.search_catalog(client, "Flaky Book")
    finally:
        await client.aclose()

    assert results[0]["availability"] == "unknown"
