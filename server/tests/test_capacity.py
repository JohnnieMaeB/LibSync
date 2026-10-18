"""AI capacity visibility (app/capacity.py): Groq's rate-limit headers,
recorded per model and summarized for GET /capacity."""

import httpx
import pytest

from app import capacity


@pytest.fixture(autouse=True)
def clean():
    capacity.reset()
    yield
    capacity.reset()


def _headers(remaining: int, limit: int = 1000) -> httpx.Headers:
    return httpx.Headers({
        "x-ratelimit-limit-requests": str(limit),
        "x-ratelimit-remaining-requests": str(remaining),
        "x-ratelimit-limit-tokens": "8000",
        "x-ratelimit-remaining-tokens": "7923",
        "x-ratelimit-reset-requests": "1m26.4s",
    })


def test_unknown_until_the_first_response(client):
    assert client.get("/capacity").json() == {"status": "unknown", "primary_model": capacity.PRIMARY_MODEL, "models": []}


@pytest.mark.parametrize(("remaining", "status"), [(999, "ok"), (99, "low"), (0, "exhausted")])
def test_status_follows_the_primary_models_daily_budget(client, remaining, status):
    capacity.record(capacity.PRIMARY_MODEL, 200, _headers(remaining))
    body = client.get("/capacity").json()
    assert body["status"] == status
    assert body["models"][0] | {"updated_seconds_ago": 0} == {
        "model": capacity.PRIMARY_MODEL,
        "requests_per_day": 1000,
        "requests_left_today": remaining,
        "tokens_per_minute": 8000,
        "tokens_left_this_minute": 7923,
        "requests_reset_in": "1m26.4s",
        "updated_seconds_ago": 0,
        "throttled_last_hour": 0,
    }


def test_rate_limited_responses_are_counted(capsys):
    capacity.record("qwen/qwen3.8-27b", 429, httpx.Headers())
    capacity.record("qwen/qwen3.8-27b", 429, httpx.Headers())
    assert capacity.snapshot()["models"][0]["throttled_last_hour"] == 2


def test_warns_once_when_the_budget_runs_low(capsys):
    capacity.record(capacity.PRIMARY_MODEL, 200, _headers(90))
    capacity.record(capacity.PRIMARY_MODEL, 200, _headers(80))
    assert capsys.readouterr().out.count("Capacity warning") == 1


async def test_the_hook_reads_the_model_from_the_request():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers=_headers(500), json={})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), event_hooks={"response": [capacity.on_response]}
    ) as client:
        await client.post("https://api.groq.com/openai/v1/chat/completions", json={"model": "openai/gpt-oss-20b"})
    assert capacity.snapshot()["models"][0]["model"] == "openai/gpt-oss-20b"
