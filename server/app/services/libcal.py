"""Springshare LibCal: room availability (Tier 8 Phase 37T, TIER8_PLAN.md §2.7)
and upcoming events (NEXT_FEATURES.md 11).

Read-only: lists which spaces in a location are free on a date, and the
library's upcoming programs. Booking and registration stay on the library's
own LibCal pages. Authenticates with LibCal API client
credentials (LibCal → Admin → API → API Authentication).

**Not yet verified against a live LibCal instance**: written to LibCal's
documented 1.1 API (/oauth/token, /space/items/{location}?availability=date,
/events?cal_id=...) and covered by mocked tests.

integrations.libcal: {"site": "library.libcal.com", "location_id": "123", "client_id": "...",
                      "booking_url": "https://library.libcal.com/reserve", "calendar_id": "456"}
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


_TAGS = re.compile(r"<[^>]+>")
MAX_DAYS = 60


def _names(values) -> str:
    return ", ".join(v["name"] for v in values or [] if isinstance(v, dict) and v.get("name"))


async def upcoming_events(
    client: httpx.AsyncClient, settings: dict, client_secret: str | None, search: str | None = None, days: int = 14
) -> list[dict]:
    """The library's programs in the next `days` days, optionally matching a
    search term: title, start and end, place, audience, a short description
    and the public page where a patron can register."""
    site = (settings.get("site") or "").strip().removeprefix("https://").rstrip("/")
    calendar_id = settings.get("calendar_id")
    client_id = settings.get("client_id")
    if not site or not calendar_id or not client_id or not client_secret:
        raise ValueError("LibCal events need integrations.libcal.site, calendar_id, client_id and the libcal_client_secret")
    base = f"https://{site}"
    token = await _token(client, base, client_id, client_secret)
    params = {"cal_id": str(calendar_id), "days": str(max(1, min(int(days), MAX_DAYS))), "limit": "8"}
    if search and search.strip():
        params["search"] = search.strip()
    response = await client.get(
        f"{base}/1.1/events", params=params, headers={"Authorization": f"Bearer {token}"}, timeout=10.0
    )
    response.raise_for_status()
    body = response.json() or {}
    events = []
    for event in body.get("events", []) if isinstance(body, dict) else []:
        location = event.get("location") or {}
        url = event.get("url") or {}
        description = " ".join(_TAGS.sub(" ", event.get("description") or "").split())
        events.append(
            {
                "title": event.get("title") or "Untitled event",
                "start": event.get("start"),
                "end": event.get("end"),
                "all_day": bool(event.get("allday")),
                "location": location.get("name") if isinstance(location, dict) else None,
                "audience": _names(event.get("audience")),
                "description": description[:240],
                "url": url.get("public") if isinstance(url, dict) else None,
            }
        )
    return events
