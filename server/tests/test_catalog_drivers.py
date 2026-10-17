"""Tier 8 Phase 32: ILS catalog drivers. SRU was also live-tested against the
Library of Congress; Koha and Polaris are verified here against their
documented APIs only (mocked)."""

import json
import xml.etree.ElementTree as ET

import httpx
import pytest
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from app.agent import chat_agent
from app.deps import LibSyncDeps
from app.library_config import LibraryConfig
from app.services import catalog, open_library_service
from app.services.catalog import koha, marc, polaris, sru

MARC_RECORD = """
<record xmlns="http://www.loc.gov/MARC21/slim">
  <controlfield tag="001">42</controlfield>
  <controlfield tag="008">200403s2021    nyu           000 1 eng  </controlfield>
  <datafield tag="010" ind1=" " ind2=" "><subfield code="a">  2020015821</subfield></datafield>
  <datafield tag="020" ind1=" " ind2=" "><subfield code="a">9780593135204 (hardback)</subfield></datafield>
  <datafield tag="100" ind1="1" ind2=" "><subfield code="a">Weir, Andy,</subfield></datafield>
  <datafield tag="245" ind1="1" ind2="0">
    <subfield code="a">Project Hail Mary :</subfield><subfield code="b">a novel /</subfield>
    <subfield code="c">Andy Weir.</subfield>
  </datafield>
  {items}
</record>
"""

AVAILABLE_ITEM = '<datafield tag="952" ind1=" " ind2=" "><subfield code="7">0</subfield></datafield>'
CHECKED_OUT_ITEM = '<datafield tag="952" ind1=" " ind2=" "><subfield code="q">2026-11-01</subfield></datafield>'


def _record(items=""):
    return ET.fromstring(MARC_RECORD.format(items=items))


def test_marc_record_to_book():
    book = marc.record_to_book(_record())
    assert book == {
        "title": "Project Hail Mary: a novel",
        "author": "Andy Weir",
        "first_publish_year": 2021,
        "cover_url": "https://covers.openlibrary.org/b/isbn/9780593135204-M.jpg?default=false",
        "url": "https://lccn.loc.gov/2020015821",
        "availability": "in catalog",
    }


@pytest.mark.parametrize(
    ("items", "expected"),
    [(AVAILABLE_ITEM, "available"), (CHECKED_OUT_ITEM, "checked out"), (CHECKED_OUT_ITEM + AVAILABLE_ITEM, "available")],
)
def test_koha_items_in_marc_give_availability(items, expected):
    assert marc.record_to_book(_record(items), items_tag="952")["availability"] == expected


def test_952_is_ignored_unless_the_server_is_koha():
    # The Library of Congress's records carry a 952 that isn't holdings data.
    assert marc.record_to_book(_record(AVAILABLE_ITEM))["availability"] == "in catalog"


def test_record_url_template():
    book = marc.record_to_book(_record(), "https://opac.example/cgi-bin/koha/opac-detail.pl?biblionumber={id}")
    assert book["url"] == "https://opac.example/cgi-bin/koha/opac-detail.pl?biblionumber=42"


@pytest.mark.parametrize(
    ("raw", "shown"),
    [("Weir, Andy", "Andy Weir"), ("Le Guin, Ursula K.", "Ursula K. Le Guin"), ("United Nations", "United Nations")],
)
def test_display_name(raw, shown):
    assert marc.display_name(raw) == shown


async def test_sru_builds_a_cql_query_and_parses_marcxml():
    seen: list[httpx.Request] = []

    def handler(request):
        seen.append(request)
        body = (
            '<zs:searchRetrieveResponse xmlns:zs="http://www.loc.gov/zing/srw/"><zs:records><zs:record><zs:recordData>'
            + MARC_RECORD.format(items="")
            + "</zs:recordData></zs:record></zs:records></zs:searchRetrieveResponse>"
        )
        return httpx.Response(200, content=body.encode())

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        books = await sru.search(client, {"base_url": "https://sru.example/biblios"}, 'hail "mary"', 3)
    assert books[0]["title"] == "Project Hail Mary: a novel"
    params = seen[0].url.params
    assert params["operation"] == "searchRetrieve"
    assert params["query"] == '"hail \\"mary\\""'
    assert params["recordSchema"] == "marcxml"


async def test_sru_requires_a_base_url():
    async with httpx.AsyncClient() as client:
        with pytest.raises(ValueError):
            await sru.search(client, {}, "x", 3)


async def test_koha_token_search_and_items():
    koha._token_cache.clear()
    calls: list[str] = []

    def handler(request: httpx.Request):
        calls.append(f"{request.method} {request.url.path}")
        if request.url.path == "/api/v1/oauth/token":
            assert b"grant_type=client_credentials" in request.content
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 3600})
        assert request.headers["authorization"] == "Bearer tok"
        if request.url.path == "/api/v1/biblios":
            query = json.loads(request.url.params["q"])
            assert query["-or"][0]["title"]["-like"] == "%hail mary%"
            return httpx.Response(200, json=[{"biblio_id": 7, "title": "Project Hail Mary /", "author": "Weir, Andy", "copyright_date": 2021}])
        if request.url.path == "/api/v1/biblios/7/items":
            return httpx.Response(200, json=[{"checked_out_date": "2026-10-01"}, {"checked_out_date": None, "not_for_loan_status": 0, "lost_status": 0}])
        return httpx.Response(404)

    settings = {"base_url": "https://staff.koha.example", "client_id": "cid", "opac_url": "https://catalog.koha.example"}
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        books = await koha.search(client, settings, "secret", "hail mary", 3)
        await koha.search(client, settings, "secret", "hail mary", 3)
    assert books == [
        {
            "title": "Project Hail Mary",
            "author": "Weir, Andy",
            "first_publish_year": 2021,
            "cover_url": None,
            "url": "https://catalog.koha.example/cgi-bin/koha/opac-detail.pl?biblionumber=7",
            "availability": "available",
        }
    ]
    assert calls.count("POST /api/v1/oauth/token") == 1  # token reused until it nears expiry


async def test_koha_requires_credentials():
    async with httpx.AsyncClient() as client:
        with pytest.raises(ValueError):
            await koha.search(client, {"base_url": "https://k.example", "client_id": "c"}, None, "x", 3)


def test_polaris_signature_is_hmac_sha1_base64():
    # Independently computed: base64(HMAC-SHA1("key", "GET" + uri + date)).
    import base64, hashlib, hmac

    uri, date = "https://papi.example/x", "Thu, 15 Oct 2026 00:00:00 GMT"
    expected = base64.b64encode(hmac.new(b"key", f"GET{uri}{date}".encode(), hashlib.sha1).digest()).decode()
    assert polaris.signature("key", "GET", uri, date) == expected


async def test_polaris_search_signs_and_parses():
    def handler(request: httpx.Request):
        assert request.headers["authorization"].startswith("PWS acc:")
        assert "PolarisDate" in request.headers
        assert "/public/v1/1033/100/1/search/bibs/keyword/KW" in request.url.path
        return httpx.Response(
            200,
            json={
                "PAPIErrorCode": 1,
                "BibSearchRows": [
                    {"Title": "Project Hail Mary", "Author": "Weir, Andy", "PublicationDate": "2021", "ISBN": "9780593135204", "ControlNumber": 99, "LocalItemsIn": 0, "LocalItemsTotal": 3}
                ],
            },
        )

    settings = {"base_url": "https://papi.example/PAPIService/REST", "access_id": "acc", "pac_url": "https://pac.example"}
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        books = await polaris.search(client, settings, "key", "hail mary", 3)
    assert books[0]["availability"] == "checked out"
    assert books[0]["first_publish_year"] == 2021
    assert books[0]["url"] == "https://pac.example/search/title.aspx?pos=1&cn=99"


async def test_polaris_error_code_raises():
    def handler(request):
        return httpx.Response(200, json={"PAPIErrorCode": -1, "ErrorMessage": "bad signature"})

    settings = {"base_url": "https://papi.example", "access_id": "acc"}
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RuntimeError, match="bad signature"):
            await polaris.search(client, settings, "key", "x", 3)


# --- dispatcher -------------------------------------------------------------

OL_BOOK = {"title": "OL", "author": "A", "first_publish_year": None, "cover_url": None, "url": None, "availability": "unknown"}


@pytest.fixture()
def open_library(monkeypatch):
    async def fake(client, query, limit=3):
        return [OL_BOOK]

    monkeypatch.setattr(open_library_service, "search_catalog", fake)


async def test_default_is_open_library(open_library):
    result = await catalog.search_catalog(None, None, "x")
    assert (result.results, result.source, result.fell_back) == ([OL_BOOK], "Open Library", False)


async def test_failing_driver_falls_back_to_open_library(open_library):
    config = LibraryConfig(id="lib", name="Lib", catalog_driver="sru", catalog_config={})  # no base_url
    result = await catalog.search_catalog(None, config, "x")
    assert result.fell_back and result.source == "Open Library" and result.results == [OL_BOOK]


async def test_driver_results_are_labeled_as_the_librarys(monkeypatch, open_library):
    async def fake_sru(client, settings, query, limit):
        return [{**OL_BOOK, "title": "Mine"}]

    monkeypatch.setattr(sru, "search", fake_sru)
    config = LibraryConfig(id="lib", name="Lib", catalog_driver="sru", catalog_config={"base_url": "https://x"})
    result = await catalog.search_catalog(None, config, "x")
    assert result.source == "the library's catalog" and result.results[0]["title"] == "Mine"


async def test_koha_driver_reads_its_secret(monkeypatch, open_library):
    seen = {}

    async def fake_secret(client, library_id, name):
        seen["secret"] = (library_id, name)
        return "s3cret"

    async def fake_koha(client, settings, secret, query, limit):
        seen["used"] = secret
        return []

    monkeypatch.setattr(catalog, "get_library_secret", fake_secret)
    monkeypatch.setattr(koha, "search", fake_koha)
    await catalog.search_catalog(None, LibraryConfig(id="lib", name="L", catalog_driver="koha"), "x")
    assert seen == {"secret": ("lib", "koha_client_secret"), "used": "s3cret"}


async def test_agent_tells_the_model_when_it_fell_back(open_library):
    returned: list[str] = []

    def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        for message in messages:
            for part in message.parts:
                if isinstance(part, ToolReturnPart):
                    returned.append(str(part.content))
                    return ModelResponse(parts=[TextPart("done")])
        return ModelResponse(parts=[ToolCallPart(tool_name="search_catalog", args={"query": "x"})])

    config = LibraryConfig(id="lib", name="L", catalog_driver="sru", catalog_config={})
    with chat_agent.override(model=FunctionModel(model)):
        await chat_agent.run("find x", deps=LibSyncDeps(http_client=None, library_config=config))
    assert "didn't respond" in returned[0] and "Open Library" in returned[0]
