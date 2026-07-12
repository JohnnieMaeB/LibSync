"""Tests for the AG-UI transport (`/agent`), covering the same behaviors
`test_chat.py` asserts for `/chat`/`/chat/stream` — session continuity, a
streamed reply, and a tool call — but through AG-UI's wire events instead of
the bespoke SSE contract."""

import json
import uuid

from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, DeltaToolCall, FunctionModel

from app import agent as agent_module
from app.agent import chat_agent


def _run_agent_input(*, thread_id: str, content: str) -> dict:
    return {
        "threadId": thread_id,
        "runId": str(uuid.uuid4()),
        "state": None,
        "messages": [{"id": str(uuid.uuid4()), "role": "user", "content": content}],
        "tools": [],
        "context": [],
        "forwardedProps": None,
    }


def _parse_sse_events(text: str) -> list[dict]:
    events = []
    for line in text.splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[len("data: ") :]))
    return events


def _last_user_prompt(messages: list[ModelMessage]) -> str:
    from pydantic_ai.messages import UserPromptPart

    last_request = messages[-1]
    for part in reversed(last_request.parts):
        if isinstance(part, UserPromptPart):
            return part.content if isinstance(part.content, str) else str(part.content)
    return ""


async def streaming_text_function(messages: list[ModelMessage], info: AgentInfo):
    for chunk in ["Hello", ", ", "world!"]:
        yield chunk


async def history_counting_stream_function(messages: list[ModelMessage], info: AgentInfo):
    yield f"message_count={len(messages)}"


async def tool_calling_stream_function(messages: list[ModelMessage], info: AgentInfo):
    for message in reversed(messages):
        for part in message.parts:
            if isinstance(part, ToolReturnPart):
                yield f"Per catalog: {part.content}"
                return
    yield {0: DeltaToolCall(name="search_catalog", json_args=json.dumps({"query": _last_user_prompt(messages)}))}


async def research_tool_calling_stream_function(messages: list[ModelMessage], info: AgentInfo):
    for message in reversed(messages):
        for part in message.parts:
            if isinstance(part, ToolReturnPart):
                yield f"Per OpenAlex: {part.content}"
                return
    yield {
        0: DeltaToolCall(
            name="search_scholarly_works", json_args=json.dumps({"query": _last_user_prompt(messages)})
        )
    }


async def citation_tool_calling_stream_function(messages: list[ModelMessage], info: AgentInfo):
    for message in reversed(messages):
        for part in message.parts:
            if isinstance(part, ToolReturnPart):
                yield f"Per Crossref: {part.content}"
                return
    yield {
        0: DeltaToolCall(
            name="lookup_and_cite", json_args=json.dumps({"style": "apa", "doi": "10.1016/j.lindif.2023.102274"})
        )
    }


class TestAgentEndpoint:
    def test_streams_run_started_text_and_run_finished(self, client):
        with chat_agent.override(model=FunctionModel(stream_function=streaming_text_function)):
            response = client.post(
                "/agent",
                json=_run_agent_input(thread_id="thread-1", content="Hi"),
                headers={"Accept": "text/event-stream"},
            )

        assert response.status_code == 200
        events = _parse_sse_events(response.text)
        event_types = [e["type"] for e in events]
        assert event_types[0] == "RUN_STARTED"
        assert event_types[-1] == "RUN_FINISHED"
        assert "TEXT_MESSAGE_CONTENT" in event_types

        text_deltas = "".join(e["delta"] for e in events if e["type"] == "TEXT_MESSAGE_CONTENT")
        assert text_deltas == "Hello, world!"

    def test_second_run_on_same_thread_receives_prior_history(self, client):
        with chat_agent.override(model=FunctionModel(stream_function=history_counting_stream_function)):
            first = client.post("/agent", json=_run_agent_input(thread_id="thread-2", content="turn one"))
            assert "".join(
                e["delta"] for e in _parse_sse_events(first.text) if e["type"] == "TEXT_MESSAGE_CONTENT"
            ) == "message_count=1"

            second = client.post("/agent", json=_run_agent_input(thread_id="thread-2", content="turn two"))
            assert "".join(
                e["delta"] for e in _parse_sse_events(second.text) if e["type"] == "TEXT_MESSAGE_CONTENT"
            ) == "message_count=3"

    def test_different_threads_do_not_share_history(self, client):
        with chat_agent.override(model=FunctionModel(stream_function=history_counting_stream_function)):
            first = client.post("/agent", json=_run_agent_input(thread_id="thread-a", content="hello"))
            other = client.post("/agent", json=_run_agent_input(thread_id="thread-b", content="hello"))

        for response in (first, other):
            deltas = "".join(e["delta"] for e in _parse_sse_events(response.text) if e["type"] == "TEXT_MESSAGE_CONTENT")
            assert deltas == "message_count=1"

    def test_tool_call_shows_start_and_result_events(self, client, monkeypatch):
        # Phase 6 only covers the transport: proves a tool call surfaces as a
        # visible TOOL_CALL_START/RESULT pair on the AG-UI stream, grounded in
        # the real catalog tool. Phase 9 adds a `book_card` CUSTOM event on
        # top of this same tool call — see its own test for that assertion.
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

        monkeypatch.setattr(agent_module.open_library_service, "search_catalog", fake_search_catalog)

        with chat_agent.override(model=FunctionModel(stream_function=tool_calling_stream_function)):
            response = client.post("/agent", json=_run_agent_input(thread_id="thread-3", content="Is Project Hail Mary available?"))

        events = _parse_sse_events(response.text)
        event_types = [e["type"] for e in events]
        assert "TOOL_CALL_START" in event_types
        assert "TOOL_CALL_RESULT" in event_types

        result_event = next(e for e in events if e["type"] == "TOOL_CALL_RESULT")
        assert "Project Hail Mary" in result_event["content"]
        assert "lendable" in result_event["content"]

    def test_catalog_tool_call_emits_a_book_card_custom_event_per_result(self, client, monkeypatch):
        async def fake_search_catalog(http_client, query: str, limit: int = 3) -> list[dict]:
            return [
                {
                    "title": "Project Hail Mary",
                    "author": "Andy Weir",
                    "first_publish_year": 2021,
                    "cover_url": "https://covers.openlibrary.org/b/id/12345-M.jpg",
                    "url": "https://openlibrary.org/works/OL123W",
                    "availability": "lendable",
                },
                {
                    "title": "The Martian",
                    "author": "Andy Weir",
                    "first_publish_year": 2011,
                    "cover_url": None,
                    "url": "https://openlibrary.org/works/OL456W",
                    "availability": "checked out",
                },
            ]

        monkeypatch.setattr(agent_module.open_library_service, "search_catalog", fake_search_catalog)

        with chat_agent.override(model=FunctionModel(stream_function=tool_calling_stream_function)):
            response = client.post("/agent", json=_run_agent_input(thread_id="thread-6", content="Any Andy Weir books?"))

        events = _parse_sse_events(response.text)
        custom_events = [e for e in events if e["type"] == "CUSTOM" and e["name"] == "book_card"]
        assert len(custom_events) == 2
        assert custom_events[0]["value"]["title"] == "Project Hail Mary"
        assert custom_events[0]["value"]["cover_url"] == "https://covers.openlibrary.org/b/id/12345-M.jpg"
        assert custom_events[0]["value"]["url"] == "https://openlibrary.org/works/OL123W"
        assert custom_events[1]["value"]["title"] == "The Martian"
        assert custom_events[1]["value"]["availability"] == "checked out"

    def test_research_tool_call_emits_research_results_custom_event(self, client, monkeypatch):
        async def fake_search_scholarly_works(http_client, query: str, limit: int = 5) -> list[dict]:
            return [
                {
                    "title": "ChatGPT for good?",
                    "authors": "Enkelejda Kasneci",
                    "year": 2023,
                    "citation_count": 5340,
                    "is_oa": True,
                    "doi": "https://doi.org/10.1016/j.lindif.2023.102274",
                    "abstract": "Large language models help.",
                }
            ]

        monkeypatch.setattr(agent_module.openalex_service, "search_scholarly_works", fake_search_scholarly_works)

        with chat_agent.override(model=FunctionModel(stream_function=research_tool_calling_stream_function)):
            response = client.post("/agent", json=_run_agent_input(thread_id="thread-4", content="find papers on large language models"))

        events = _parse_sse_events(response.text)
        event_types = [e["type"] for e in events]
        assert "TOOL_CALL_START" in event_types
        assert "TOOL_CALL_RESULT" in event_types

        custom_events = [e for e in events if e["type"] == "CUSTOM"]
        assert len(custom_events) == 1
        assert custom_events[0]["name"] == "research_results"
        assert custom_events[0]["value"]["works"][0]["title"] == "ChatGPT for good?"
        assert custom_events[0]["value"]["works"][0]["citation_count"] == 5340
        assert custom_events[0]["value"]["works"][0]["is_oa"] is True

    def test_citation_tool_call_emits_citation_custom_event(self, client, monkeypatch):
        async def fake_lookup_work(http_client, *, doi=None, title=None) -> dict:
            assert doi == "10.1016/j.lindif.2023.102274"
            return {
                "DOI": doi,
                "type": "journal-article",
                "title": ["ChatGPT for good?"],
                "author": [{"given": "Enkelejda", "family": "Kasneci"}],
                "container-title": ["Learning and Individual Differences"],
                "issued": {"date-parts": [[2023]]},
            }

        monkeypatch.setattr(agent_module.crossref_service, "lookup_work", fake_lookup_work)

        with chat_agent.override(model=FunctionModel(stream_function=citation_tool_calling_stream_function)):
            response = client.post("/agent", json=_run_agent_input(thread_id="thread-5", content="cite this in APA: 10.1016/j.lindif.2023.102274"))

        events = _parse_sse_events(response.text)
        custom_events = [e for e in events if e["type"] == "CUSTOM"]
        assert len(custom_events) == 1
        assert custom_events[0]["name"] == "citation"
        assert custom_events[0]["value"]["style"] == "apa"
        assert custom_events[0]["value"]["doi"] == "10.1016/j.lindif.2023.102274"
        assert "Kasneci" in custom_events[0]["value"]["formatted"]
        assert set(custom_events[0]["value"]["available_styles"]) == {"apa", "mla", "chicago"}


class TestCitationStyleSwitchEndpoint:
    def test_reformats_a_known_doi_in_the_requested_style(self, client, monkeypatch):
        async def fake_lookup_work(http_client, *, doi=None, title=None) -> dict:
            return {
                "DOI": doi,
                "type": "journal-article",
                "title": ["ChatGPT for good?"],
                "author": [{"given": "Enkelejda", "family": "Kasneci"}],
                "container-title": ["Learning and Individual Differences"],
                "issued": {"date-parts": [[2023]]},
            }

        monkeypatch.setattr(agent_module.crossref_service, "lookup_work", fake_lookup_work)

        response = client.get("/citation/10.1016/j.lindif.2023.102274", params={"style": "mla"})

        assert response.status_code == 200
        body = response.json()
        assert body["style"] == "mla"
        assert body["doi"] == "10.1016/j.lindif.2023.102274"
        assert "Kasneci" in body["formatted"]

    def test_defaults_to_apa_when_no_style_given(self, client, monkeypatch):
        async def fake_lookup_work(http_client, *, doi=None, title=None) -> dict:
            return {"DOI": doi, "type": "journal-article", "title": ["X"], "author": []}

        monkeypatch.setattr(agent_module.crossref_service, "lookup_work", fake_lookup_work)

        response = client.get("/citation/10.1/x")

        assert response.status_code == 200
        assert response.json()["style"] == "apa"

    def test_returns_400_for_unsupported_style(self, client):
        response = client.get("/citation/10.1/x", params={"style": "vancouver"})
        assert response.status_code == 400
        assert "error" in response.json()

    def test_returns_404_when_doi_not_found(self, client, monkeypatch):
        async def fake_lookup_work(http_client, *, doi=None, title=None) -> None:
            return None

        monkeypatch.setattr(agent_module.crossref_service, "lookup_work", fake_lookup_work)

        response = client.get("/citation/10.0000/does-not-exist")
        assert response.status_code == 404
