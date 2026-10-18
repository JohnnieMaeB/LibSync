"""AI capacity visibility (NEXT_FEATURES.md P2.8).

Groq's free tier is LibSync's scaling ceiling: about 1,000 requests a day per
model, and a per-minute token budget. Groq reports both on every response
(`x-ratelimit-*` headers: "requests" is the daily budget, "tokens" the
per-minute one). This records the latest headers per model, counts
rate-limited responses, and summarizes them for `GET /capacity` and the staff
dashboard, with a log warning when the primary model's daily budget runs low.

In memory, per process: Render runs a single instance, and a restart resets
nothing that matters (the next response carries fresh numbers).
"""

import json
import time
from collections import deque

import httpx

LOW_SHARE = 0.10  # warn below 10% of the daily requests left
PRIMARY_MODEL = "openai/gpt-oss-120b"

_latest: dict[str, dict] = {}
_throttled: dict[str, deque[float]] = {}
_warned_low: set[str] = set()


def _model(request: httpx.Request) -> str:
    try:
        return json.loads(request.content or b"{}").get("model") or "unknown"
    except Exception:
        return "unknown"


def _int(value: str | None) -> int | None:
    return int(value) if value and value.isdigit() else None


def record(model: str, status: int, headers: httpx.Headers) -> None:
    now = time.time()
    if status == 429:
        window = _throttled.setdefault(model, deque())
        window.append(now)
    limit = _int(headers.get("x-ratelimit-limit-requests"))
    remaining = _int(headers.get("x-ratelimit-remaining-requests"))
    if limit is None or remaining is None:
        return
    _latest[model] = {
        "requests_per_day": limit,
        "requests_left_today": remaining,
        "tokens_per_minute": _int(headers.get("x-ratelimit-limit-tokens")),
        "tokens_left_this_minute": _int(headers.get("x-ratelimit-remaining-tokens")),
        "requests_reset_in": headers.get("x-ratelimit-reset-requests"),
        "at": now,
    }
    low = remaining < limit * LOW_SHARE
    if low and model not in _warned_low:
        _warned_low.add(model)
        print(f"Capacity warning: {model} has {remaining} of {limit} daily requests left.")
    elif not low:
        _warned_low.discard(model)


async def on_response(response: httpx.Response) -> None:
    """httpx response hook for the Groq client."""
    record(_model(response.request), response.status_code, response.headers)


def snapshot() -> dict:
    """What the dashboard shows: per model, the latest budget and how many
    rate-limited responses in the last hour; overall, ok / low / exhausted /
    unknown (no response seen since the process started)."""
    now = time.time()
    models = []
    for model in sorted(set(_latest) | set(_throttled)):
        window = _throttled.get(model, deque())
        while window and now - window[0] > 3600:
            window.popleft()
        latest = _latest.get(model, {})
        models.append(
            {
                "model": model,
                **{key: value for key, value in latest.items() if key != "at"},
                "updated_seconds_ago": round(now - latest["at"]) if latest else None,
                "throttled_last_hour": len(window),
            }
        )
    primary = _latest.get(PRIMARY_MODEL)
    if primary is None:
        status = "unknown"
    elif primary["requests_left_today"] == 0:
        status = "exhausted"
    elif primary["requests_left_today"] < primary["requests_per_day"] * LOW_SHARE:
        status = "low"
    else:
        status = "ok"
    return {"status": status, "primary_model": PRIMARY_MODEL, "models": models}


def reset() -> None:
    """For tests."""
    _latest.clear()
    _throttled.clear()
    _warned_low.clear()
