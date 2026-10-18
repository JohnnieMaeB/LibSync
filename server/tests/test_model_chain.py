"""The model fallback chain, including the optional OpenRouter step and its
privacy routing (app/agent.py)."""

from app import agent


def test_without_a_key_the_chain_is_unchanged():
    names = [m.model_name for m in agent.model_chain(None)]
    assert names == ["openai/gpt-oss-120b", "qwen/qwen3.8-27b", "openai/gpt-oss-20b", "deepseek-ai/DeepSeek-V4-Flash"]


def test_with_a_key_openrouter_comes_before_the_hugging_face_credit():
    chain = agent.model_chain("sk-or-test")
    assert [m.model_name for m in chain][3] == agent.OPENROUTER_FREE_MODELS[0]
    assert chain[-1].model_name == "deepseek-ai/DeepSeek-V4-Flash"


def test_openrouter_only_routes_to_providers_that_keep_nothing():
    settings = agent.model_chain("sk-or-test")[3].settings
    assert settings["openrouter_provider"] == {"data_collection": "deny", "zdr": True}
    assert settings["openrouter_models"] == agent.OPENROUTER_FREE_MODELS[1:]


async def test_the_privacy_routing_is_in_the_request_openrouter_receives(monkeypatch):
    import json

    import httpx
    from pydantic_ai import Agent
    from pydantic_ai.providers.openrouter import OpenRouterProvider

    sent: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "id": "x",
                "object": "chat.completion",
                "created": 0,
                "model": agent.OPENROUTER_FREE_MODELS[0],
                "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": "ok"}}],
            },
        )

    real_provider = OpenRouterProvider

    def provider_with_mock(api_key):
        return real_provider(api_key=api_key, http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))

    monkeypatch.setattr("pydantic_ai.providers.openrouter.OpenRouterProvider", provider_with_mock)
    model = agent._openrouter_model("sk-or-test")
    try:
        await Agent(model).run("hi")
    except Exception:
        pass  # the stub reply isn't a full OpenRouter response; only the request matters here
    assert sent[0]["provider"] == {"data_collection": "deny", "zdr": True}
    assert sent[0]["models"] == agent.OPENROUTER_FREE_MODELS[1:]
