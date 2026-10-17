"""Springshare LibCal room availability — Tier 8 Phase 37T (TIER8_PLAN.md §2.7).

Read-only: lists which spaces in a location are free on a date. Booking stays
on the library's own LibCal page. Authenticates with LibCal API client
credentials (LibCal → Admin → API → API Authentication).

**Not yet verified against a live LibCal instance**: written to LibCal's
documented 1.1 API (/oauth/token, /space/items/{location}?availability=date)
and covered by mocked tests.

integrations.libcal: {"site": "library.libcal.com", "location_id": "123", "client_id": "...",
                      "booking_url": "https://library.libcal.com/reserve"}
secret: library_secrets.libcal_client_secret
"""

import re
import time

import httpx

_token_cache: dict[str, tuple[float, str]] = {}
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


async def _token(client: httpx.AsyncClient, base: str, client_id: str, client_secret: str) -> str:
    key = f"{base}|{client_id}"
    cached = _token_cache.get(key)
    if cached and cached[0] > time.monotonic():
        return cached[1]
    response = await client.post(
        f"{base}/1.1/oauth/token",
        data={"grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret},
        timeout=10.0,
    )
    response.raise_for_status()
    body = response.json()
    _token_cache[key] = (time.monotonic() + max(int(body.get("expires_in", 3600)) - 60, 0), body["access_token"])
    return body["access_token"]


def _times(slot: dict) -> str:
    def hhmm(value: str) -> str:
        match = re.search(r"T(\d{2}:\d{2})", value or "")
        return match.group(1) if match else value

    return f"{hhmm(slot.get('from', ''))}–{hhmm(slot.get('to', ''))}"


async def room_availability(client: httpx.AsyncClient, settings: dict, client_secret: str | None, date: str) -> list[dict]:
    site = (settings.get("site") or "").strip().removeprefix("https://").rstrip("/")
    location_id = settings.get("location_id")
    client_id = settings.get("client_id")
    if not site or not location_id or not client_id or not client_secret:
        raise ValueError("LibCal needs integrations.libcal.site, location_id, client_id and the libcal_client_secret")
    if not _DATE.match(date):
        raise ValueError("date must be YYYY-MM-DD")
    base = f"https://{site}"
    token = await _token(client, base, client_id, client_secret)
    response = await client.get(
        f"{base}/1.1/space/items/{location_id}",
        params={"availability": date},
        headers={"Authorization": f"Bearer {token}"},
        timeout=10.0,
    )
    response.raise_for_status()
    rooms = []
    for space in response.json() or []:
        slots = space.get("availability") or []
        rooms.append(
            {
                "name": space.get("name") or f"Space {space.get('id')}",
                "capacity": space.get("capacity"),
                "free": [_times(s) for s in slots[:8]],
            }
        )
    return rooms
