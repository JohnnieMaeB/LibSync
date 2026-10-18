"""Tier 9 Phases 35-36: the SIP2 client (against a fake SIP2 server speaking
the protocol over a real socket), patron sessions, and the sign-in routes."""

import asyncio
import time

import pytest

from app import library_config, patron_auth
from app.library_config import LibraryConfig
from app.routers import libraries as libraries_router
from app.routers import patrons as patrons_router
from app.services import sip2
from app.services.sip2 import PatronStatus, SIP2Client, SIP2Error

CARD, PIN = "21234000567890", "4321"
HEADER = "              001" + "20261017    120000"  # status(14) + language + date(18)
TITLES = {"3001": "The Overstory", "3002": "Dune"}  # barcode 3999 has no title on file


def _reply(body: str) -> bytes:
    # Koha ends replies with CR LF by default; the client must cope.
    return sip2.frame(body, 0).encode() + b"\n"


async def _fake_sip2_server(seen: list[str]):
    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        while True:
            try:
                line = (await reader.readuntil(b"\r")).decode()
            except asyncio.IncompleteReadError:
                break
            seen.append(line)
            # Every message LibSync sends must carry a valid checksum.
            body, check = line.rstrip("\r").rsplit("AZ", 1)
            assert sip2.checksum(body + "AZ") == check
            if line.startswith("93"):
                writer.write(_reply("941" if "COsippass|" in line else "940"))
            elif line.startswith("23"):
                good = f"AA{CARD}|" in line and f"AD{PIN}|" in line
                known = f"AA{CARD}|" in line
                writer.write(_reply(f"24{HEADER}AOinst|AA{CARD}|AEJane Doe|BL{'Y' if known else 'N'}|CQ{'Y' if good else 'N'}|BV0.00|"))
            elif line.startswith("63"):
                counts = "0001" + "0001" + "0002" + "0000" + "0000" + "0000"
                # Like Koha: only the first "Y" in the summary picks a list.
                # Like Koha, lists carry barcodes, not titles.
                lists = {0: "AS3001|", 1: "AT3002|", 2: "AU3002|AU3999|"}
                chosen = lists.get(line[23:33].find("Y"), "")
                writer.write(_reply(f"64{HEADER}{counts}AOinst|AA{CARD}|AEJane Doe|BLY|{chosen}BV1.50|"))
            elif line.startswith("17"):
                barcode = sip2.parse_fields(line[20:]).get("AB", "")
                title = TITLES.get(barcode, "")
                writer.write(_reply(f"18030001{'20261017    120000'}AB{barcode}|AJ{title}|"))
            await writer.drain()
        writer.close()

    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    return server, server.sockets[0].getsockname()[1]


def _settings(port):
    return {"host": "127.0.0.1", "port": port, "tls": False, "institution_id": "inst", "login_user": "libsync"}


def test_checksum_makes_the_byte_sum_zero():
    message = "9300CNuser|COpass|CPloc|AY0AZ"
    total = sum(message.encode()) + int(sip2.checksum(message), 16)
    assert total & 0xFFFF == 0


def test_tls_is_on_unless_explicitly_off():
    base = {"host": "h", "login_user": "u"}
    assert SIP2Client({**base}, "p").use_tls is True
    assert SIP2Client({**base, "tls": "true"}, "p").use_tls is True
    assert SIP2Client({**base, "tls": "false"}, "p").use_tls is False


def test_field_parsing_keeps_repeated_item_fields():
    assert sip2.parse_fields("AUone|AUtwo|BLY|") == {"AU": "one\ntwo", "BL": "Y"}


async def test_verify_patron_over_a_real_socket():
    seen: list[str] = []
    server, port = await _fake_sip2_server(seen)
    async with server:
        async with SIP2Client(_settings(port), "sippass") as client:
            good = await client.verify_patron(CARD, PIN)
            wrong_pin = await client.verify_patron(CARD, "0000")
    assert (good.valid_patron, good.valid_password) == (True, True)
    assert (wrong_pin.valid_patron, wrong_pin.valid_password) == (True, False)
    assert seen[0].startswith("9300CNlibsync|COsippass|")
    assert seen[1].startswith("23001")


async def test_patron_information_counts_and_items():
    seen: list[str] = []
    server, port = await _fake_sip2_server(seen)
    async with server:
        async with SIP2Client(_settings(port), "sippass") as client:
            info = await client.patron_information(CARD)
    assert info.counts["charged"] == 2 and info.counts["holds"] == 1
    # Barcodes are turned into titles (17 Item Information); one without a title stays as-is.
    assert info.items == {"holds": ["The Overstory"], "overdue": ["Dune"], "charged": ["Dune", "3999"]}
    assert info.fee_amount == "1.50"
    assert all("AD" not in line for line in seen[1:])  # the PIN is never sent for account lookups
    assert [line[23:33] for line in seen[1:] if line.startswith("63")] == ["Y         ", " Y        ", "  Y       "]


async def test_rejected_sip_login_raises():
    server, port = await _fake_sip2_server([])
    async with server:
        with pytest.raises(SIP2Error):
            async with SIP2Client(_settings(port), "wrong"):
                pass


def test_pipes_in_input_cannot_inject_fields():
    assert sip2._escape("123|ADsteal|") == "123ADsteal"


# --- sessions ---------------------------------------------------------------


@pytest.fixture()
def secret(monkeypatch):
    monkeypatch.setattr(patron_auth, "PATRON_SESSION_SECRET", "test-secret-value")


def test_session_round_trip_carries_no_pin(secret):
    token, session = patron_auth.issue("springfield-pl", "card", CARD, card=CARD)
    assert PIN not in token and CARD not in token  # encrypted, opaque
    verified = patron_auth.verify(token)
    assert verified.library_id == "springfield-pl" and verified.card == CARD
    assert verified.patron_ref == patron_auth.patron_ref("springfield-pl", CARD)


def test_patron_ref_differs_per_library(secret):
    assert patron_auth.patron_ref("a", CARD) != patron_auth.patron_ref("b", CARD)


def test_tampered_or_expired_tokens_are_rejected(secret, monkeypatch):
    token, _ = patron_auth.issue("springfield-pl", "email", "email:u1")
    assert patron_auth.verify(token[:-4] + "AAAA") is None
    monkeypatch.setattr(time, "time", lambda: 10**12)
    assert patron_auth.verify(token) is None


def test_sessions_off_without_a_secret():
    assert patron_auth.verify("anything") is None


# --- routes -----------------------------------------------------------------

SIP2_LIBRARY = LibraryConfig(id="springfield-pl", name="S", integrations={"sip2": {"host": "sip.example", "login_user": "u"}})


@pytest.fixture()
def library(monkeypatch, secret):
    async def config(client, library_id):
        return SIP2_LIBRARY if library_id == "springfield-pl" else None

    async def password(client, library_id, name):
        return "sippass"

    monkeypatch.setattr(patrons_router, "get_library_config", config)
    monkeypatch.setattr(patrons_router, "get_library_secret", password)


class _FakeSIP:
    def __init__(self, status=None, error=None):
        self.status, self.error = status, error

    def __call__(self, settings, password):
        return self

    async def __aenter__(self):
        if self.error:
            raise self.error
        return self

    async def __aexit__(self, *exc):
        return False

    async def verify_patron(self, card, pin):
        return self.status


HEADERS = {"X-LibSync-Library": "springfield-pl"}


def test_card_sign_in_issues_a_session(client, library, monkeypatch):
    monkeypatch.setattr(patrons_router, "SIP2Client", _FakeSIP(PatronStatus(True, True)))
    body = client.post("/patron/sign-in/card", json={"card": CARD, "pin": PIN}, headers=HEADERS).json()
    session = patron_auth.verify(body["token"])
    assert body["kind"] == "card" and session.card == CARD
    me = client.get("/patron/me", headers={"X-LibSync-Patron": body["token"]})
    assert me.json()["library_id"] == "springfield-pl"


def test_wrong_pin_is_a_generic_401(client, library, monkeypatch):
    monkeypatch.setattr(patrons_router, "SIP2Client", _FakeSIP(PatronStatus(True, False)))
    response = client.post("/patron/sign-in/card", json={"card": CARD, "pin": "0000"}, headers=HEADERS)
    assert response.status_code == 401 and "weren't recognized" in response.json()["detail"]


def test_sip2_outage_is_a_502(client, library, monkeypatch):
    monkeypatch.setattr(patrons_router, "SIP2Client", _FakeSIP(error=OSError("refused")))
    response = client.post("/patron/sign-in/card", json={"card": CARD, "pin": PIN}, headers=HEADERS)
    assert response.status_code == 502


def test_libraries_without_accounts_say_so(client, library):
    response = client.post("/patron/sign-in/card", json={"card": CARD, "pin": PIN}, headers={"X-LibSync-Library": "other"})
    assert response.status_code == 404


def test_me_requires_a_valid_session(client, secret):
    assert client.get("/patron/me").status_code == 401
    assert client.get("/patron/me", headers={"X-LibSync-Patron": "forged"}).status_code == 401


def test_public_settings_list_sign_in_methods(client, monkeypatch, secret):
    async def config(client_, library_id):
        return SIP2_LIBRARY

    monkeypatch.setattr(libraries_router, "get_library_config", config)
    monkeypatch.setattr(library_config, "SUPABASE_URL", None)
    assert client.get("/libraries/springfield-pl").json()["patron_sign_in"] == ["card"]
