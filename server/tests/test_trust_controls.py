"""Phase 36T (TIER8_PLAN.md §2.8): a library can switch tool groups off from
its embed snippet, and patron messages stay out of traces by default."""

import pytest
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from app import config
from app.agent import chat_agent
from app.deps import LibSyncDeps
from app.tenants import TOOL_GROUPS, parse_enabled_tools

# The two vendor tools (Phase 37T) are hidden unless the library configured them.
ALL_TOOLS = set(TOOL_GROUPS.values()) - {"check_ebook_availability", "check_room_availability", "check_my_account"}


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, None),
        ("   ", None),
        ("catalog", frozenset({"catalog"})),
        (" Policies , CATALOG ", frozenset({"policies", "catalog"})),
        ("catalog,made-up", frozenset({"catalog"})),
        ("made-up", frozenset()),
    ],
)
def test_parse_enabled_tools(raw, expected):
    assert parse_enabled_tools(raw) == expected


def _model_seeing_tools(seen: list[set[str]]) -> FunctionModel:
    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        seen.append({tool.name for tool in info.function_tools})
        return ModelResponse(parts=[TextPart("ok")])

    return FunctionModel(respond)


@pytest.mark.parametrize(
    ("enabled", "visible"),
    [
        (None, ALL_TOOLS),
        (frozenset({"catalog"}), {"search_catalog"}),
        (frozenset({"policies", "citations"}), {"search_library_policies", "lookup_and_cite"}),
        (frozenset(), set()),
    ],
)
async def test_switched_off_tools_are_hidden_from_the_model(enabled, visible):
    seen: list[set[str]] = []
    with chat_agent.override(model=_model_seeing_tools(seen)):
        await chat_agent.run("hi", deps=LibSyncDeps(http_client=None, enabled_tools=enabled))
    assert seen == [visible]


def test_tools_header_reaches_the_agent_through_chat(client):
    seen: list[set[str]] = []
    with chat_agent.override(model=_model_seeing_tools(seen)):
        response = client.post("/chat", json={"message": "hi"}, headers={"X-LibSync-Tools": "research"})
    assert response.status_code == 200
    assert seen == [{"search_scholarly_works"}]


def test_trace_content_is_off_unless_explicitly_enabled():
    assert config.LOGFIRE_INCLUDE_CONTENT is False
