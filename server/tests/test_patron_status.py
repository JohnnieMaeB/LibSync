"""Tier 9 Phase 38: the signed-in patron's account tool. The model gets only
counts; titles go straight to the patron's screen."""

import pytest
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from app import agent as agent_module
from app import patron_auth
from app.agent import chat_agent
from app.deps import LibSyncDeps
from app.library_config import LibraryConfig
from app.services.sip2 import PatronStatus

SIP2_LIBRARY = LibraryConfig(id="springfield-pl", name="S", integrations={"sip2": {"host": "h", "login_user": "u"}})
CARD_SESSION = patron_auth.PatronSession("springfield-pl", "ref", "card", card="21234000567890", expires_at=0)


class _FakeSIP:
    def __call__(self, settings, password):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def patron_information(self, card):
        assert card == "21234000567890"
        return PatronStatus(
            True,
            True,
            counts={"charged": 2, "overdue": 1, "holds": 1},
            items={"charged": ["Dune", "Beloved"], "overdue": ["Dune"], "holds": ["The Overstory"]},
            fee_amount="1.50",
        )


@pytest.fixture()
def fake_sip(monkeypatch):
    async def password(client, library_id, name):
        return "pw"

    monkeypatch.setattr(agent_module, "SIP2Client", _FakeSIP())
    monkeypatch.setattr(agent_module, "get_library_secret", password)


def _tools_seen(deps):
    seen = {}

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        seen["tools"] = {t.name for t in info.function_tools}
        seen["instructions"] = info.instructions or ""
        return ModelResponse(parts=[TextPart("ok")])

    return seen, FunctionModel(respond)


@pytest.mark.parametrize(
    ("patron", "config", "visible"),
    [
        (None, SIP2_LIBRARY, False),
        (CARD_SESSION, SIP2_LIBRARY, True),
        (patron_auth.PatronSession("springfield-pl", "ref", "email"), SIP2_LIBRARY, False),
        (CARD_SESSION, LibraryConfig(id="springfield-pl", name="S"), False),
    ],
)
async def test_account_tool_only_for_card_patrons_at_sip2_libraries(patron, config, visible):
    seen, model = _tools_seen(None)
    with chat_agent.override(model=model):
        await chat_agent.run("hi", deps=LibSyncDeps(http_client=None, library_config=config, patron=patron))
    assert ("check_my_account" in seen["tools"]) is visible
    assert ("check_my_account" in seen["instructions"]) is visible


async def test_model_gets_counts_and_the_patron_gets_titles(fake_sip):
    returned = {}

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        for message in messages:
            for part in message.parts:
                if isinstance(part, ToolReturnPart):
                    returned["content"] = str(part.content)
                    returned["metadata"] = part.metadata
                    return ModelResponse(parts=[TextPart("done")])
        return ModelResponse(parts=[ToolCallPart(tool_name="check_my_account", args={})])

    with chat_agent.override(model=FunctionModel(respond)):
        await chat_agent.run(
            "what do I have out?", deps=LibSyncDeps(http_client=None, library_config=SIP2_LIBRARY, patron=CARD_SESSION)
        )
    assert "2 item(s) checked out" in returned["content"] and "1 overdue" in returned["content"]
    for title in ("Dune", "Beloved", "The Overstory"):
        assert title not in returned["content"]  # never sent to the AI provider
    event = returned["metadata"]
    assert event.name == "account_summary"
    assert event.value["items"]["charged"] == ["Dune", "Beloved"]


def test_a_session_for_another_library_is_ignored(client, monkeypatch):
    from app import request_gate

    monkeypatch.setattr(patron_auth, "PATRON_SESSION_SECRET", "s")
    token, _ = patron_auth.issue("other-library", "card", "c", card="c")
    seen = {}

    async def config(client_, library_id):
        return SIP2_LIBRARY

    monkeypatch.setattr(request_gate, "get_library_config", config)

    async def respond(messages: list[ModelMessage], info: AgentInfo):
        seen["tools"] = {t.name for t in info.function_tools}
        yield "ok"

    body = {
        "threadId": "t", "runId": "r", "state": None, "tools": [], "context": [], "forwardedProps": None,
        "messages": [{"id": "m", "role": "user", "content": "hi"}],
    }
    with chat_agent.override(model=FunctionModel(stream_function=respond)):
        client.post("/agent", json=body, headers={"X-LibSync-Library": "springfield-pl", "X-LibSync-Patron": token})
    assert "check_my_account" not in seen["tools"]
