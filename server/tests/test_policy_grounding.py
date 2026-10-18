"""Policy answers may only state numbers the policy search returned
(NEXT_FEATURES.md P0.1). Includes the exact wrong answer seen in production."""

import pytest
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from app import agent as agent_module
from app.agent import POLICY_GROUNDING_RETRIES, chat_agent
from app.deps import LibSyncDeps
from app.grounding import quantities, unsupported_quantities

POLICY = (
    "- Books may be borrowed for a period of three weeks. Renewals are available online.\n"
    "- Items may be renewed up to three times online or by phone, as long as no one else has placed a hold on them.\n"
    "- A fine of $0.25 per day is charged for overdue items."
)


def test_the_production_embellishment_is_caught():
    reply = (
        "You can borrow a book for **three weeks**. Most books can be renewed online "
        "(usually up to 2 additional three-week periods). Overdue items incur $0.25 per day."
    )
    assert unsupported_quantities(reply, [POLICY]) == ["2"]


@pytest.mark.parametrize(
    "reply",
    [
        "Borrow for 21 days and renew up to 3 times.",  # units converted
        "Fines are 25 cents a day.",  # dollars <-> cents
        "Fines are $0.25 per day.",
        "1. Log in\n2. Choose Renew\nYou can renew three times.",  # list markers ignored
        "One thing to know: renewals need no one else to have a hold.",  # generic "one"
    ],
)
def test_supported_answers_pass(reply):
    assert unsupported_quantities(reply, [POLICY]) == []


def test_numbers_from_the_patrons_question_are_allowed():
    reply = "No, it isn't $1 a day; it's $0.25 per day."
    assert unsupported_quantities(reply, [POLICY]) == ["$1"]
    assert unsupported_quantities(reply, [POLICY, "My friend said fines are $1 a day."]) == []


@pytest.mark.parametrize(
    ("reply", "unsupported"),
    [
        ("Puede pedir libros por tres semanas y renovarlos hasta tres veces.", []),
        ("Puede pedir libros por 21 días. La multa es de 25 centavos por día.", []),  # converted units
        ("Puede renovarlos hasta dos veces más.", ["dos"]),  # the production error, in Spanish
    ],
)
def test_spanish_answers_are_checked_too(reply, unsupported):
    assert unsupported_quantities(reply, [POLICY]) == unsupported


def test_english_once_is_not_a_number():
    assert unsupported_quantities("Once you return it, you can renew online.", [POLICY]) == []


def test_quantities_keep_their_units():
    assert quantities("$5.00 cap, 48 hours ahead, two weeks") == [(5.0, "$"), (48.0, "hours"), (2.0, "weeks")]


# --- the validator in the agent ----------------------------------------------


def _policy_then(answers: list[str]):
    """A model that searches policies, then gives `answers` in order (one per retry)."""
    replies = iter(answers)

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        searched = any(isinstance(p, ToolReturnPart) for m in messages for p in getattr(m, "parts", []))
        if not searched:
            return ModelResponse(parts=[ToolCallPart(tool_name="search_library_policies", args={"query": "renew"})])
        return ModelResponse(parts=[TextPart(next(replies))])

    return FunctionModel(respond)


@pytest.fixture()
def policy_index(monkeypatch):
    def fake_search(query, top_k=3, namespace="ns1"):
        return {"matches": [{"text": line.lstrip("- ")} for line in POLICY.splitlines()]}

    monkeypatch.setattr(agent_module, "search_pinecone", fake_search)
    monkeypatch.setattr(agent_module, "policy_namespace", lambda library_id: "ns1")


async def test_an_unsupported_number_gets_a_retry(policy_index):
    with chat_agent.override(model=_policy_then(["Renew up to 2 more times.", "Renew up to three times."])):
        result = await chat_agent.run("How many renewals?", deps=LibSyncDeps(http_client=None))
    assert result.output == "Renew up to three times."


async def test_persistent_errors_fall_back_to_the_policy_text(policy_index):
    wrong = ["Renew up to 2 more times."] * (POLICY_GROUNDING_RETRIES + 1)
    with chat_agent.override(model=_policy_then(wrong)):
        result = await chat_agent.run("How many renewals?", deps=LibSyncDeps(http_client=None))
    assert result.output.startswith("Here's what the library's policy says:")
    assert "renewed up to three times" in result.output
    assert " 2 " not in result.output


async def test_non_policy_answers_are_not_checked():
    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[TextPart("Hi! I can help with 2 or 3 things at once.")])

    with chat_agent.override(model=FunctionModel(respond)):
        result = await chat_agent.run("hello", deps=LibSyncDeps(http_client=None))
    assert result.output.startswith("Hi!")
