"""Per-library usage statistics from Logfire traces — Tier 8 Phase 33
(TIER8_PLAN.md §2.3). No second logging pipeline: every agent run already
carries `library_id` in its run metadata (PR #49), so stats are SQL over the
spans pydantic-ai emits.

Span shapes (pydantic-ai instrumentation v5, verified in its source): agent
runs are `invoke_agent ...` spans with a JSON `metadata` attribute; tool calls
are `execute_tool ...` spans with `gen_ai.tool.name`. Message text is never
read (and isn't recorded; see LOGFIRE_INCLUDE_CONTENT).

Needs LOGFIRE_READ_TOKEN (a Logfire *read* token, separate from the write
token). Without it the stats endpoint answers 503 and nothing else changes.
"""

from datetime import UTC, datetime, timedelta

from app.config import LOGFIRE_READ_TOKEN
from app.tenants import TOOL_GROUPS

MAX_DAYS = 90
_KNOWN_TOOLS = set(TOOL_GROUPS.values())


def stats_enabled() -> bool:
    return bool(LOGFIRE_READ_TOKEN)


def _library_filter(library_id: str) -> str:
    # library_id is validated as [a-z0-9-] (app/tenants.py), so it is safe to
    # embed. The LIKE matches the compact JSON pydantic-ai writes for run
    # metadata ({"library_id":"..."}), confirmed from captured spans in
    # tests/test_usage_stats.py. `kind = 'span'` skips Logfire's pending
    # (in-progress) copies of each span, which would double-count.
    assert all(c.isalnum() or c == "-" for c in library_id)
    return f"""attributes->>'metadata' LIKE '%"library_id":"{library_id}"%'"""


def daily_sql(library_id: str) -> str:
    return f"""
        SELECT date_trunc('day', start_timestamp) AS day,
               count(*) AS turns,
               sum(CASE WHEN is_exception OR upper(otel_status_code) = 'ERROR' THEN 1 ELSE 0 END) AS errors
        FROM records
        WHERE kind = 'span' AND span_name LIKE 'invoke_agent%' AND {_library_filter(library_id)}
        GROUP BY day
        ORDER BY day
    """


def tools_sql(library_id: str) -> str:
    return f"""
        SELECT attributes->>'gen_ai.tool.name' AS tool, count(*) AS calls
        FROM records
        WHERE kind = 'span' AND span_name LIKE 'execute_tool%'
          AND trace_id IN (
            SELECT trace_id FROM records
            WHERE span_name LIKE 'invoke_agent%' AND {_library_filter(library_id)}
          )
        GROUP BY tool
        ORDER BY calls DESC
    """


async def library_stats(library_id: str, days: int, client_factory=None) -> dict:
    days = max(1, min(days, MAX_DAYS))
    since = datetime.now(UTC) - timedelta(days=days)
    if client_factory is None:
        from logfire.query_client import AsyncLogfireQueryClient

        client_factory = lambda: AsyncLogfireQueryClient(read_token=LOGFIRE_READ_TOKEN)  # noqa: E731
    async with client_factory() as client:
        daily = (await client.query_json_rows(sql=daily_sql(library_id), min_timestamp=since))["rows"]
        tools = (await client.query_json_rows(sql=tools_sql(library_id), min_timestamp=since))["rows"]

    turns = sum(int(row["turns"]) for row in daily)
    errors = sum(int(row["errors"] or 0) for row in daily)
    return {
        "days": days,
        "turns": turns,
        "errors": errors,
        "error_rate": round(errors / turns, 4) if turns else 0.0,
        "daily": [{"day": str(row["day"])[:10], "turns": int(row["turns"]), "errors": int(row["errors"] or 0)} for row in daily],
        # Only the four patron-facing tools; pydantic-ai's output tool is noise here.
        "tools": [{"tool": row["tool"], "calls": int(row["calls"])} for row in tools if row["tool"] in _KNOWN_TOOLS],
    }
