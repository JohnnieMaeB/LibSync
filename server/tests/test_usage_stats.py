"""Tier 8 Phase 33: per-library usage stats over Logfire traces."""

import logfire
import pytest
from fastapi import HTTPException
from logfire.testing import CaptureLogfire
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

from app import usage_stats
from app.agent import chat_agent
from app.deps import LibSyncDeps
from app.routers import stats as stats_router
from app.staff_auth import StaffMember


async def test_real_spans_match_what_the_queries_look_for(capfire: CaptureLogfire):
    """Guards the SQL's assumptions against pydantic-ai changing its span
    names or metadata format: run the agent, capture the real spans, and check
    them against the same patterns the queries use."""
    logfire.instrument_pydantic_ai(include_content=False)
    try:
        with chat_agent.override(model=TestModel(call_tools=["lookup_and_cite"])):
            await chat_agent.run("cite", deps=LibSyncDeps(http_client=None, library_id="springfield-pl"))
    finally:
        Agent.instrument_all(False)

    spans = capfire.exporter.exported_spans
    runs = [s for s in spans if s.name.startswith("invoke_agent") and "metadata" in (s.attributes or {})]
    tools = [s for s in spans if s.name.startswith("execute_tool")]
    assert runs, [s.name for s in spans]
    assert '"library_id":"springfield-pl"' in runs[-1].attributes["metadata"]
    assert any(s.attributes.get("gen_ai.tool.name") == "lookup_and_cite" for s in tools)
    assert "LIKE 'invoke_agent%'" in usage_stats.daily_sql("springfield-pl")
    assert """'%"library_id":"springfield-pl"%'""" in usage_stats.daily_sql("springfield-pl")


def test_library_id_cannot_inject_sql():
    with pytest.raises(AssertionError):
        usage_stats.daily_sql("x'; drop table records; --")


class _FakeQueryClient:
    def __init__(self, daily, tools):
        self.results = [daily, tools]
        self.sql: list[str] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def query_json_rows(self, sql, min_timestamp):
        self.sql.append(sql)
        return {"rows": self.results.pop(0)}


async def test_aggregates_turns_errors_and_known_tools():
    fake = _FakeQueryClient(
        daily=[{"day": "2026-10-14T00:00:00Z", "turns": 10, "errors": 1}, {"day": "2026-10-15T00:00:00Z", "turns": 30, "errors": None}],
        tools=[{"tool": "search_library_policies", "calls": 12}, {"tool": "final_result", "calls": 9}],
    )
    result = await usage_stats.library_stats("springfield-pl", 500, client_factory=lambda: fake)
    assert result["days"] == usage_stats.MAX_DAYS
    assert (result["turns"], result["errors"], result["error_rate"]) == (40, 1, 0.025)
    assert result["daily"] == [
        {"day": "2026-10-14", "turns": 10, "errors": 1},
        {"day": "2026-10-15", "turns": 30, "errors": 0},
    ]
    assert result["tools"] == [{"tool": "search_library_policies", "calls": 12}]


@pytest.fixture()
def staff(monkeypatch):
    async def fake_staff(request, library_id, admin=False):
        return StaffMember(user_id="u", email=None, role="staff")

    monkeypatch.setattr(stats_router, "require_staff", fake_staff)


def test_endpoint_is_503_without_a_read_token(client, staff, monkeypatch):
    monkeypatch.setattr(stats_router, "stats_enabled", lambda: False)
    assert client.get("/admin/libraries/springfield-pl/stats").status_code == 503


def test_endpoint_returns_stats(client, staff, monkeypatch):
    async def fake_stats(library_id, days):
        return {"days": days, "turns": 3}

    monkeypatch.setattr(stats_router, "stats_enabled", lambda: True)
    monkeypatch.setattr(stats_router, "library_stats", fake_stats)
    assert client.get("/admin/libraries/springfield-pl/stats?days=7").json() == {"days": 7, "turns": 3}


def test_endpoint_requires_staff(client, monkeypatch):
    async def deny(request, library_id, admin=False):
        raise HTTPException(status_code=403, detail="no")

    monkeypatch.setattr(stats_router, "require_staff", deny)
    assert client.get("/admin/libraries/springfield-pl/stats").status_code == 403
