"""Tier 8 Phase 37T: OverDrive and LibCal tools, and per-library
instructions. Vendor APIs are mocked (no credentials to test live)."""

import httpx
import pytest
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from app.agent import chat_agent
from app.deps import LibSyncDeps
from app.library_config import LibraryConfig
from app.services import libcal, overdrive


@pytest.fixture(autouse=True)
def clear_caches():
    overdrive._token_cache.clear()
    overdrive._collection_cache.clear()
    libcal._token_cache.clear()


async def test_overdrive_search_with_availability():
    def handler(request: httpx.Request):
        if request.url.host == "oauth.overdrive.com":
            assert request.headers["authorization"].startswith("Basic ")
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 3600})
        assert request.headers["authorization"] == "Bearer tok"
        if request.url.path == "/v1/libraries/1234":
            return httpx.Response(200, json={"collectionToken": "coll"})
        if request.url.path == "/v1/collections/coll/products":
            assert request.url.params["q"] == "hail mary"
            return httpx.Response(
                200,
                json={
                    "products": [
                        {
                            "title": "Project Hail Mary",
                            "primaryCreator": {"name": "Andy Weir"},
                            "formats": [{"name": "OverDrive Listen audiobook"}],
                            "links": {"availability": {"href": "https://api.overdrive.com/v2/avail/1"}},
                        }
                    ]
                },
            )
        if request.url.path == "/v2/avail/1":
            return httpx.Response(200, json={"copiesOwned": 4, "copiesAvailable": 0, "numberOfHolds": 9})
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        rows = await overdrive.search_availability(client, {"library_id": 1234, "client_id": "cid"}, "sec", "hail mary")
    assert rows == [
        {
            "title": "Project Hail Mary",
            "creator": "Andy Weir",
            "formats": ["OverDrive Listen audiobook"],
            "copies_available": 0,
            "copies_owned": 4,
            "holds": 9,
        }
    ]


async def test_overdrive_needs_credentials():
    async with httpx.AsyncClient() as client:
        with pytest.raises(ValueError):
            await overdrive.search_availability(client, {"library_id": 1}, None, "x")


async def test_libcal_room_availability():
    def handler(request: httpx.Request):
        if request.url.path == "/1.1/oauth/token":
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 3600})
        assert request.url.path == "/1.1/space/items/55"
        assert request.url.params["availability"] == "2026-10-20"
        return httpx.Response(
            200,
            json=[
                {
                    "id": 1,
                    "name": "Study Room A",
                    "capacity": 6,
                    "availability": [{"from": "2026-10-20T15:00:00-05:00", "to": "2026-10-20T15:30:00-05:00"}],
                }
            ],
        )

    settings = {"site": "https://lib.libcal.com/", "location_id": "55", "client_id": "cid"}
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        rooms = await libcal.room_availability(client, settings, "sec", "2026-10-20")
    assert rooms == [{"name": "Study Room A", "capacity": 6, "free": ["15:00–15:30"]}]


async def test_libcal_rejects_a_bad_date():
    async with httpx.AsyncClient() as client:
        with pytest.raises(ValueError, match="YYYY-MM-DD"):
            await libcal.room_availability(client, {"site": "x", "location_id": "1", "client_id": "c"}, "s", "tomorrow")


def _capture(seen: dict):
    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        seen["tools"] = {t.name for t in info.function_tools}
        seen["instructions"] = info.instructions or ""
        return ModelResponse(parts=[TextPart("ok")])

    return FunctionModel(respond)


async def _run(config):
    seen: dict = {}
    with chat_agent.override(model=_capture(seen)):
        await chat_agent.run("hi", deps=LibSyncDeps(http_client=None, library_config=config))
    return seen


async def test_vendor_tools_hidden_without_configuration():
    seen = await _run(LibraryConfig(id="lib", name="L"))
    assert "check_ebook_availability" not in seen["tools"]
    assert "check_room_availability" not in seen["tools"]
    assert "connected" not in seen["instructions"]


async def test_configured_vendors_add_tools_and_guidance():
    config = LibraryConfig(
        id="lib",
        name="L",
        help_url="https://lib.example/ask",
        integrations={"overdrive": {"library_id": "1"}, "libcal": {"site": "lib.libcal.com"}},
    )
    seen = await _run(config)
    assert {"check_ebook_availability", "check_room_availability"} <= seen["tools"]
    assert "https://lib.example/ask" in seen["instructions"]
    assert "check_ebook_availability" in seen["instructions"]


async def test_switching_a_vendor_group_off_hides_its_tool():
    config = LibraryConfig(id="lib", name="L", integrations={"overdrive": {"library_id": "1"}})
    seen: dict = {}
    with chat_agent.override(model=_capture(seen)):
        await chat_agent.run(
            "hi", deps=LibSyncDeps(http_client=None, library_config=config, enabled_tools=frozenset({"catalog"}))
        )
    assert "check_ebook_availability" not in seen["tools"]
