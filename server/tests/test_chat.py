import json

import pytest
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.messages import (
    ModelMessage,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.function import AgentInfo, FunctionModel

from app import agent as agent_module
from app import tenants
from app.agent import chat_agent

MOCK_REPLY_PREFIX = "Mock reply for: "
FALLBACK_REPLY_PREFIX = "Fallback reply for: "


def _last_user_prompt(messages: list[ModelMessage]) -> str:
    last_request = messages[-1]
    for part in reversed(last_request.parts):
        if isinstance(part, UserPromptPart):
            return part.content if isinstance(part.content, str) else str(part.content)
    return ""


async def mock_model_function(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    prompt = _last_user_prompt(messages)
    return ModelResponse(parts=[TextPart(f"{MOCK_REPLY_PREFIX}{prompt}")])


async def failing_model_function(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    raise RuntimeError("Mocked HF failure")


async def http_error_model_function(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    raise ModelHTTPError(status_code=429, model_name="mock-primary", body="rate limited")


async def fallback_model_function(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    prompt = _last_user_prompt(messages)
    return ModelResponse(parts=[TextPart(f"{FALLBACK_REPLY_PREFIX}{prompt}")])


@pytest.fixture()
def mock_agent():
    with chat_agent.override(model=FunctionModel(mock_model_function)):
        yield


@pytest.fixture()
def failing_agent():
    with chat_agent.override(model=FunctionModel(failing_model_function)):
        yield


@pytest.fixture()
def fallback_agent():
    """Simulates the real primary/fallback wiring: primary raises a provider
    API error (e.g. Groq rate-limited), and the fallback model should serve
    the reply instead of the request failing outright."""
    primary = FunctionModel(http_error_model_function)
    fallback = FunctionModel(fallback_model_function)
    with chat_agent.override(model=FallbackModel(primary, fallback)):
        yield


searched_namespaces: list[str] = []


def fake_search_pinecone(text: str, top_k: int = 5, namespace: str = "ns1") -> dict:
    searched_namespaces.append(namespace)
    return {
        "matches": [
            {
                "id": "pol3",
                "score": 0.95,
                "text": "A fine of $0.25 per day is charged for overdue items.",
                "category": "fines",
            }
        ]
    }


async def tool_calling_model_function(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    """Issues a search_library_policies tool call on the first turn, then
    grounds its final reply in whatever the tool returned."""
    for message in reversed(messages):
        for part in message.parts:
            if isinstance(part, ToolReturnPart):
                return ModelResponse(parts=[TextPart(f"Per policy: {part.content}")])
    return ModelResponse(
        parts=[ToolCallPart(tool_name="search_library_policies", args={"query": _last_user_prompt(messages)})]
    )


@pytest.fixture()
def tool_calling_agent(monkeypatch):
    monkeypatch.setattr(agent_module, "search_pinecone", fake_search_pinecone)
    # Namespace resolution would otherwise ask the real index which tenant
    # namespaces exist.
    monkeypatch.setattr(tenants, "list_namespaces", lambda: ["ns1", "example-library"])
    tenants.reset_namespace_cache()
    searched_namespaces.clear()
    with chat_agent.override(model=FunctionModel(tool_calling_model_function)):
        yield


async def fake_search_catalog(http_client, query: str, limit: int = 3) -> list[dict]:
    return [
        {
            "title": "Project Hail Mary",
            "author": "Andy Weir",
            "first_publish_year": 2021,
            "cover_url": "https://covers.openlibrary.org/b/id/12345-M.jpg",
            "availability": "lendable",
        }
    ]


async def catalog_tool_calling_model_function(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    """Issues a search_catalog tool call on the first turn, then grounds its
    final reply in whatever the tool returned."""
    for message in reversed(messages):
        for part in message.parts:
            if isinstance(part, ToolReturnPart):
                return ModelResponse(parts=[TextPart(f"Per catalog: {part.content}")])
    return ModelResponse(
        parts=[ToolCallPart(tool_name="search_catalog", args={"query": _last_user_prompt(messages)})]
    )


@pytest.fixture()
def catalog_tool_calling_agent(monkeypatch):
    monkeypatch.setattr(agent_module.open_library_service, "search_catalog", fake_search_catalog)
    with chat_agent.override(model=FunctionModel(catalog_tool_calling_model_function)):
        yield


async def history_counting_model_function(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    """Echoes back how many messages it was given, so tests can confirm
    prior turns are actually threaded through via message_history."""
    return ModelResponse(parts=[TextPart(f"message_count={len(messages)}")])


@pytest.fixture()
def history_counting_agent():
    with chat_agent.override(model=FunctionModel(history_counting_model_function)):
        yield


BOOK_RESULT_ARGS = {
    "intro": "Found one match:",
    "books": [
        {
            "title": "Project Hail Mary",
            "author": "Andy Weir",
            "first_publish_year": 2021,
            "cover_url": "https://covers.openlibrary.org/b/id/12345-M.jpg",
            "availability": "lendable",
        }
    ],
}


async def structured_book_result_model_function(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    """Answers directly with the structured BookResult output tool, skipping
    search_catalog — this test is only about the output_type plumbing."""
    return ModelResponse(parts=[ToolCallPart(tool_name="final_result", args=BOOK_RESULT_ARGS)])


@pytest.fixture()
def structured_book_result_agent():
    with chat_agent.override(model=FunctionModel(structured_book_result_model_function)):
        yield


async def streaming_text_function(messages: list[ModelMessage], info: AgentInfo):
    for chunk in ["Hello", ", ", "world!"]:
        yield chunk


@pytest.fixture()
def streaming_text_agent():
    with chat_agent.override(model=FunctionModel(stream_function=streaming_text_function)):
        yield


async def failing_stream_function(messages: list[ModelMessage], info: AgentInfo):
    raise RuntimeError("stream failed")
    yield  # pragma: no cover — unreachable, keeps this an async generator


@pytest.fixture()
def failing_streaming_agent():
    with chat_agent.override(model=FunctionModel(stream_function=failing_stream_function)):
        yield


def _parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.strip().split("\n\n"):
        if not block:
            continue
        event_name = None
        data = None
        for line in block.splitlines():
            if line.startswith("event: "):
                event_name = line[len("event: ") :]
            elif line.startswith("data: "):
                data = json.loads(line[len("data: ") :])
        events.append((event_name, data))
    return events


class TestChatEndpoint:
    def test_returns_reply_for_valid_message(self, client, mock_agent):
        response = client.post("/chat", json={"message": "Hello, AI!"})
        assert response.status_code == 200
        assert isinstance(response.json()["reply"], str)

    def test_returns_400_if_message_missing(self, client, mock_agent):
        response = client.post("/chat", json={})
        assert response.status_code == 400
        assert "error" in response.json()

    def test_handles_model_errors_and_returns_500(self, client, failing_agent):
        response = client.post("/chat", json={"message": "Trigger failure"})
        assert response.status_code == 500
        assert "error" in response.json()

    def test_handles_very_large_messages(self, client, mock_agent):
        large = "x" * 10000
        response = client.post("/chat", json={"message": large})
        assert response.status_code == 200
        assert "x" in response.json()["reply"]

    def test_returns_400_for_non_json_content(self, client, mock_agent):
        response = client.post("/chat", content="plain text", headers={"Content-Type": "text/plain"})
        assert response.status_code in (400, 415)

    def test_falls_back_to_secondary_model_on_primary_api_error(self, client, fallback_agent):
        response = client.post("/chat", json={"message": "Hello, AI!"})
        assert response.status_code == 200
        assert response.json()["reply"] == f"{FALLBACK_REPLY_PREFIX}Hello, AI!"

    def test_policy_question_triggers_pinecone_tool_and_grounds_reply(self, client, tool_calling_agent):
        response = client.post("/chat", json={"message": "How much are late fees?"})
        assert response.status_code == 200
        assert "$0.25 per day" in response.json()["reply"]
        assert searched_namespaces == ["ns1"]

    @pytest.mark.parametrize(
        ("header", "expected_namespace"),
        [
            ("example-library", "example-library"),  # has its own documents
            ("Example-Library", "example-library"),  # ids are case-insensitive slugs
            ("new-library", "ns1"),  # no namespace yet -> shared demo policies
            ("../../ns-other", "ns1"),  # malformed -> treated as no library
        ],
    )
    def test_policy_search_uses_the_embedding_librarys_namespace(
        self, client, tool_calling_agent, header, expected_namespace
    ):
        response = client.post(
            "/chat",
            json={"message": "How much are late fees?"},
            headers={"X-LibSync-Library": header, "Origin": "https://library.example"},
        )
        assert response.status_code == 200
        assert searched_namespaces == [expected_namespace]

    def test_book_question_triggers_catalog_tool_and_grounds_reply(self, client, catalog_tool_calling_agent):
        response = client.post("/chat", json={"message": "Is Project Hail Mary available?"})
        assert response.status_code == 200
        assert "Project Hail Mary" in response.json()["reply"]
        assert "lendable" in response.json()["reply"]

    def test_returns_a_session_id_when_none_is_provided(self, client, mock_agent):
        response = client.post("/chat", json={"message": "Hello"})
        assert response.status_code == 200
        assert isinstance(response.json()["session_id"], str)
        assert response.json()["session_id"]

    def test_echoes_back_a_provided_session_id(self, client, mock_agent):
        response = client.post("/chat", json={"message": "Hello", "session_id": "my-session"})
        assert response.status_code == 200
        assert response.json()["session_id"] == "my-session"

    def test_structured_book_result_is_returned_as_an_object(self, client, structured_book_result_agent):
        response = client.post("/chat", json={"message": "Is Project Hail Mary available?"})
        assert response.status_code == 200
        reply = response.json()["reply"]
        assert isinstance(reply, dict)
        assert reply["intro"] == "Found one match:"
        assert reply["books"][0]["title"] == "Project Hail Mary"
        assert reply["books"][0]["availability"] == "lendable"


class TestSessionContinuity:
    def test_second_turn_in_same_session_receives_prior_history(self, client, history_counting_agent):
        first = client.post("/chat", json={"message": "turn one"})
        assert first.status_code == 200
        session_id = first.json()["session_id"]
        assert first.json()["reply"] == "message_count=1"

        second = client.post("/chat", json={"message": "turn two", "session_id": session_id})
        assert second.status_code == 200
        assert second.json()["session_id"] == session_id
        assert second.json()["reply"] == "message_count=3"

        third = client.post("/chat", json={"message": "turn three", "session_id": session_id})
        assert third.json()["reply"] == "message_count=5"

    def test_different_sessions_do_not_share_history(self, client, history_counting_agent):
        first = client.post("/chat", json={"message": "hello", "session_id": "session-a"})
        assert first.json()["reply"] == "message_count=1"

        other = client.post("/chat", json={"message": "hello", "session_id": "session-b"})
        assert other.json()["reply"] == "message_count=1"


class TestChatStreamEndpoint:
    def test_streams_session_text_and_done_events(self, client, streaming_text_agent):
        response = client.post("/chat/stream", json={"message": "Hi"})
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")

        events = _parse_sse(response.text)
        event_names = [name for name, _ in events]
        assert event_names[0] == "session"
        assert event_names[-1] == "done"
        assert "text" in event_names

        session_id = events[0][1]["session_id"]
        assert session_id

        text_events = [data["text"] for name, data in events if name == "text"]
        assert text_events[-1] == "Hello, world!"

    def test_returns_400_if_message_missing(self, client, streaming_text_agent):
        response = client.post("/chat/stream", json={})
        assert response.status_code == 400
        assert "error" in response.json()

    def test_emits_error_event_on_model_failure(self, client, failing_streaming_agent):
        response = client.post("/chat/stream", json={"message": "Hi"})
        assert response.status_code == 200

        events = _parse_sse(response.text)
        event_names = [name for name, _ in events]
        assert event_names[0] == "session"
        assert "error" in event_names
        assert "done" not in event_names

    def test_reuses_provided_session_id(self, client, streaming_text_agent):
        response = client.post("/chat/stream", json={"message": "Hi", "session_id": "stream-session"})
        events = _parse_sse(response.text)
        assert events[0][1]["session_id"] == "stream-session"


class TestRateLimiting:
    def test_allows_a_single_request(self, client, mock_agent):
        response = client.post("/chat", json={"message": "test"})
        assert response.status_code == 200

    def test_returns_429_after_limit_exceeded(self, client, mock_agent):
        for _ in range(100):
            client.post("/chat", json={"message": "test"})

        response = client.post("/chat", json={"message": "test"})
        assert response.status_code == 429
        assert response.json() == {"error": "Too many requests, please try again later."}
