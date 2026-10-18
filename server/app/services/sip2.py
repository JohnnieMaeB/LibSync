"""A minimal SIP2 client — Tier 8 Phase 35, the plumbing for Tier 9's
"sign in with your library card" (TIER9_PLAN.md §2.1).

SIP2 (3M Standard Interchange Protocol 2.0) is how e-resource vendors, proxies
and self-checkout kiosks check a card against any ILS. Messages are ASCII
lines ending in a carriage return: a two-digit command, fixed-width fields,
then pipe-delimited variable fields (two-letter code + value). With error
detection on, each message also carries a sequence number (AY) and checksum
(AZ).

Only what LibSync needs: login as the library's SIP account (93/94), verify a
patron's card and PIN (23/24), and read a patron's account summary (63/64).

**Security:** SIP2 replies include the patron's personal details whether or
not the caller needs them, so connections should use TLS (or a VPN tunnel);
LibSync keeps only the yes/no answer and counts, never the PIN or the
personal fields. Written to the SIP2 2.0 specification and tested against a
fake server; not yet run against a library's real SIP2 server.

integrations.sip2: {"host": "...", "port": 6001, "tls": true, "institution_id": "...",
                    "login_user": "...", "location": "..."}
secret: library_secrets.sip2_password
"""

import asyncio
import ssl
from dataclasses import dataclass, field
from datetime import datetime

TIMEOUT_SECONDS = 10.0


class SIP2Error(Exception):
    pass


def checksum(message: str) -> str:
    """SIP2 checksum: the two's complement of the 16-bit sum of every
    character up to and including "AZ", as four uppercase hex digits."""
    total = sum(message.encode("ascii", errors="replace")) & 0xFFFF
    return f"{(-total) & 0xFFFF:04X}"


def frame(body: str, sequence: int) -> str:
    message = f"{body}AY{sequence % 10}AZ"
    return message + checksum(message) + "\r"


def sip_date(now: datetime | None = None) -> str:
    # 18 characters: YYYYMMDD, 4 spaces for the timezone, HHMMSS.
    return (now or datetime.now()).strftime("%Y%m%d    %H%M%S")


def parse_fields(variable: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for part in variable.split("|"):
        if len(part) >= 2:
            code, value = part[:2], part[2:]
            # Repeatable fields (AS/AT/AU item lists) keep every value.
            fields[code] = f"{fields[code]}\n{value}" if code in fields else value
    return fields


def _escape(value: str) -> str:
    # A pipe or carriage return would corrupt the message framing.
    return value.replace("|", "").replace("\r", "").replace("\n", "")


@dataclass
class PatronStatus:
    valid_patron: bool
    valid_password: bool
    counts: dict[str, int] = field(default_factory=dict)
    items: dict[str, list[str]] = field(default_factory=dict)
    fee_amount: str | None = None
    screen_message: str | None = None


class SIP2Client:
    def __init__(self, settings: dict, password: str | None):
        self.host = settings.get("host")
        self.port = int(settings.get("port") or 6001)
        # Dashboard settings are text: only an explicit "false"/"0"/"no" turns TLS off.
        self.use_tls = str(settings.get("tls", "true")).strip().lower() not in ("false", "0", "no")
        self.institution = settings.get("institution_id") or ""
        self.login_user = settings.get("login_user")
        self.location = settings.get("location") or ""
        self.password = password
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._sequence = 0
        if not self.host or not self.login_user or not password:
            raise SIP2Error("SIP2 needs integrations.sip2.host, login_user and the sip2_password secret")

    async def __aenter__(self) -> "SIP2Client":
        context = ssl.create_default_context() if self.use_tls else None
        self._reader, self._writer = await asyncio.wait_for(
            asyncio.open_connection(self.host, self.port, ssl=context), TIMEOUT_SECONDS
        )
        response = await self._send(f"9300CN{_escape(self.login_user)}|CO{_escape(self.password)}|CP{_escape(self.location)}|")
        if not response.startswith("941"):
            raise SIP2Error("The library's SIP2 server rejected LibSync's login")
        return self

    async def __aexit__(self, *exc) -> None:
        if self._writer:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except Exception:
                pass

    async def _send(self, body: str) -> str:
        assert self._reader and self._writer
        self._writer.write(frame(body, self._sequence).encode("ascii", errors="replace"))
        self._sequence += 1
        await self._writer.drain()
        raw = await asyncio.wait_for(self._reader.readuntil(b"\r"), TIMEOUT_SECONDS)
        # Servers may end messages with CR LF (Koha does by default); the LF
        # then arrives at the start of the next read, so strip both ends.
        return raw.decode("ascii", errors="replace").strip("\r\n")

    async def verify_patron(self, card: str, pin: str) -> PatronStatus:
        """23 Patron Status: is this a valid card, and is the PIN right?"""
        response = await self._send(
            f"23001{sip_date()}AO{_escape(self.institution)}|AA{_escape(card)}|AC|AD{_escape(pin)}|"
        )
        if not response.startswith("24") or len(response) < 37:
            raise SIP2Error("Unexpected reply to a patron status request")
        fields = parse_fields(response[37:])
        return PatronStatus(
            valid_patron=fields.get("BL") == "Y",
            valid_password=fields.get("CQ") == "Y",
            fee_amount=fields.get("BV"),
            screen_message=fields.get("AF"),
        )

    async def _patron_information(self, card: str, summary: str) -> tuple[dict[str, int], dict[str, str]]:
        response = await self._send(
            f"63001{sip_date()}{summary}AO{_escape(self.institution)}|AA{_escape(card)}|AC|BP1|BQ10|"
        )
        if not response.startswith("64") or len(response) < 61:
            raise SIP2Error("Unexpected reply to a patron information request")
        counts_raw = response[37:61]
        names = ["holds", "overdue", "charged", "fines", "recalls", "unavailable_holds"]
        counts = {}
        for i, name in enumerate(names):
            chunk = counts_raw[i * 4 : i * 4 + 4].strip()
            counts[name] = int(chunk) if chunk.isdigit() else 0
        return counts, parse_fields(response[61:])

    async def patron_information(self, card: str) -> PatronStatus:
        """63 Patron Information: counts plus the hold, overdue and charged
        item lists. Asked without the patron's PIN; LibSync verified card
        ownership at sign-in, and the library's SIP account authorizes the
        lookup.

        The spec allows one item list per request (a single "Y" in the
        summary field) and Koha honors only the first, so this asks once per
        list on the same connection."""
        counts: dict[str, int] = {}
        fields: dict[str, str] = {}
        items: dict[str, list[str]] = {}
        # Summary position 0 = hold items (AS), 1 = overdue (AT), 2 = charged (AU).
        for position, (name, code) in enumerate((("holds", "AS"), ("overdue", "AT"), ("charged", "AU"))):
            list_counts, list_fields = await self._patron_information(card, (" " * position + "Y").ljust(10))
            counts = counts or list_counts
            fields = fields or list_fields
            items[name] = [i for i in list_fields.get(code, "").split("\n") if i]
        return PatronStatus(
            valid_patron=fields.get("BL") == "Y",
            valid_password=fields.get("CQ") == "Y",
            counts=counts,
            items=items,
            fee_amount=fields.get("BV"),
            screen_message=fields.get("AF"),
        )
