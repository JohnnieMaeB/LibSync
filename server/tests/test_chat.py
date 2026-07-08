import pytest
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from app.agent import chat_agent

MOCK_REPLY_PREFIX = "Mock reply for: "


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


@pytest.fixture()
def mock_agent():
    with chat_agent.override(model=FunctionModel(mock_model_function)):
        yield


@pytest.fixture()
def failing_agent():
    with chat_agent.override(model=FunctionModel(failing_model_function)):
        yield


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
