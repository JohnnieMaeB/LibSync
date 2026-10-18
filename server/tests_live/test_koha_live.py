"""LibSync's Koha drivers against a real Koha (koha-testing-docker), not mocks.

Run by .github/workflows/koha-live.yml, which starts KTD, seeds it with
.github/koha/seed.pl and passes the results in KOHA_LIVE_* variables.
Skipped everywhere else.
"""

import json
import os
import re

import httpx
import pytest

from app.services import sip2
from app.services.catalog import koha, sru

SEED = json.loads(os.environ.get("KOHA_LIVE_SEED") or "{}")
pytestmark = pytest.mark.skipif(not SEED, reason="needs a seeded koha-testing-docker (KOHA_LIVE_SEED)")

STAFF_URL = os.environ.get("KOHA_LIVE_STAFF_URL", "")
OPAC_URL = os.environ.get("KOHA_LIVE_OPAC_URL", "")
SRU_URL = os.environ.get("KOHA_LIVE_SRU_URL", "")
SIP_HOST = os.environ.get("KOHA_LIVE_SIP_HOST", "")
SIP_PORT = int(os.environ.get("KOHA_LIVE_SIP_PORT") or 6001)
SIP_SETTINGS = {
    "host": SIP_HOST,
    "port": SIP_PORT,
    "tls": "false",  # KTD's SIP server is plain TCP; production libraries should use TLS
    "institution_id": "kohalibrary",
    "login_user": "koha",
    "location": SEED.get("branch", ""),
}
VALID_AVAILABILITY = {"available", "checked out", "in catalog"}


def _normalized(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()


def _search_words(title: str, count: int = 3) -> str:
    return " ".join(re.findall(r"[A-Za-z]{3,}", title)[:count])


def _is_seeded_title(found: str) -> bool:
    seeded, found = _normalized(SEED["title"]), _normalized(found)
    return bool(found) and (seeded.startswith(found) or found.startswith(seeded))


async def test_koha_rest_finds_the_seeded_book_and_its_checkout():
    settings = {"base_url": STAFF_URL, "client_id": SEED["client_id"], "opac_url": OPAC_URL}
    async with httpx.AsyncClient() as client:
        books = await koha.search(client, settings, SEED["client_secret"], SEED["title"], limit=5)
    print("Koha REST results:", books)
    assert books, "Koha REST search returned nothing for a title that exists"
    assert all(book["availability"] in VALID_AVAILABILITY for book in books)
    seeded = [b for b in books if b["url"] and b["url"].endswith(f"biblionumber={SEED['biblio_id']}")]
    assert seeded, "the seeded biblio was not among the results"
    # Its only copy was checked out by the seed script.
    assert seeded[0]["availability"] == "checked out"


async def test_koha_rest_rejects_a_wrong_secret():
    koha._token_cache.clear()
    settings = {"base_url": STAFF_URL, "client_id": SEED["client_id"]}
    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.HTTPStatusError):
            await koha.search(client, settings, "not-the-secret", "anything", limit=1)


async def test_sru_finds_the_seeded_book_with_item_data():
    if not SRU_URL:
        pytest.skip("no SRU endpoint")
    settings = {"base_url": SRU_URL, "items_tag": "952"}
    async with httpx.AsyncClient() as client:
        books = await sru.search(client, settings, _search_words(SEED["title"]), limit=10)
    print("SRU results:", books)
    assert books, "SRU search returned nothing for words from a title that exists"
    seeded = [b for b in books if _is_seeded_title(b["title"])]
    assert seeded, "the seeded title was not among the SRU results"
    # 952 items were read (a record without them would say "in catalog").
    assert seeded[0]["availability"] in ("available", "checked out")


async def test_sip2_signs_in_the_seeded_patron():
    async with sip2.SIP2Client(SIP_SETTINGS, "koha") as client:
        status = await client.verify_patron(SEED["card"], SEED["pin"])
    print("SIP2 patron status:", status)
    assert status.valid_patron and status.valid_password


async def test_sip2_rejects_a_wrong_pin():
    async with sip2.SIP2Client(SIP_SETTINGS, "koha") as client:
        status = await client.verify_patron(SEED["card"], "wrong-pin")
    assert status.valid_patron and not status.valid_password


async def test_sip2_rejects_an_unknown_card():
    async with sip2.SIP2Client(SIP_SETTINGS, "koha") as client:
        status = await client.verify_patron("NO-SUCH-CARD-000", "x")
    assert not status.valid_patron


async def test_sip2_rejects_a_wrong_sip_login():
    with pytest.raises(sip2.SIP2Error):
        async with sip2.SIP2Client(SIP_SETTINGS, "not-the-password"):
            pass


async def test_sip2_account_summary_counts_the_checkout():
    async with sip2.SIP2Client(SIP_SETTINGS, "koha") as client:
        info = await client.patron_information(SEED["card"])
    print("SIP2 patron information:", info)
    assert info.valid_patron
    assert info.counts["charged"] == 1
    assert len(info.items["charged"]) == 1
