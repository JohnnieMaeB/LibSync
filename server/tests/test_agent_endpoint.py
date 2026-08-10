"""Tests for the AG-UI transport (`/agent`), covering the same behaviors
`test_chat.py` asserts for `/chat`/`/chat/stream` — session continuity, a
streamed reply, and a tool call — but through AG-UI's wire events instead of
the bespoke SSE contract."""

import json
import uuid

import pytest
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, DeltaToolCall, FunctionModel

from app import agent as agent_module
from app.agent import chat_agent
from app.widget_registry import widget_registry


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


def _run_agent_input_with_messages(*, thread_id: str, messages: list[dict]) -> dict:
    return {
        "threadId": thread_id,
        "runId": str(uuid.uuid4()),
        "state": None,
        "messages": [{"id": str(uuid.uuid4()), **message} for message in messages],
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


def _flaky_stream_function(*, fail_times: int, reply: str = "Recovered reply"):
    """Builds a stream function that raises for the first `fail_times` calls
    (simulating Groq's intermittent tool_use_failed error escaping mid-stream,
    see `_run_stream_with_retry` in app/routers/agent.py) and streams `reply`
    on every call after that. Returns the function plus a mutable call
    counter so tests can assert exactly how many attempts were made."""
    calls = {"count": 0}

    async def stream_function(messages: list[ModelMessage], info: AgentInfo):
        calls["count"] += 1
        if calls["count"] <= fail_times:
            raise RuntimeError("Failed to call a function. Please adjust your prompt. See 'failed_generation' for more details.")
        yield reply

    return stream_function, calls


def _always_failing_stream_function():
    calls = {"count": 0}

    async def stream_function(messages: list[ModelMessage], info: AgentInfo):
        calls["count"] += 1
        raise RuntimeError("Failed to call a function. Please adjust your prompt. See 'failed_generation' for more details.")
        yield  # pragma: no cover — unreachable, keeps this an async generator

    return stream_function, calls


async def _fail_after_one_chunk_stream_function(messages: list[ModelMessage], info: AgentInfo):
    yield "Partial"
    raise RuntimeError("Failed to call a function. Please adjust your prompt. See 'failed_generation' for more details.")


class TestAgentEndpointRetriesTransientToolCallFailures:
    """Regression coverage for the live bug caught testing PR #42: Groq's
    tool_use_failed error occasionally escapes FallbackModel's fallback
    boundary (which only guards stream *entry*, not iteration of an
    already-entered stream) and reached patrons as a raw RUN_ERROR — observed
    live at roughly a 2-in-3 failure rate for "Find me a sci-fi audiobook"."""

    def test_retries_and_recovers_when_failure_happens_before_any_content(self, client):
        stream_function, calls = _flaky_stream_function(fail_times=1)
        with chat_agent.override(model=FunctionModel(stream_function=stream_function)):
            response = client.post("/agent", json=_run_agent_input(thread_id="retry-1", content="Find me a sci-fi audiobook"))

        assert calls["count"] == 2
        events = _parse_sse_events(response.text)
        event_types = [e["type"] for e in events]
        assert "RUN_ERROR" not in event_types
        assert event_types.count("RUN_STARTED") == 1
        assert event_types[-1] == "RUN_FINISHED"
        text_deltas = "".join(e["delta"] for e in events if e["type"] == "TEXT_MESSAGE_CONTENT")
        assert text_deltas == "Recovered reply"

    def test_gives_up_after_max_attempts_and_surfaces_the_last_error(self, client):
        stream_function, calls = _always_failing_stream_function()
        with chat_agent.override(model=FunctionModel(stream_function=stream_function)):
            response = client.post("/agent", json=_run_agent_input(thread_id="retry-2", content="Find me a sci-fi audiobook"))

        assert calls["count"] == 3  # _MAX_AGENT_RUN_ATTEMPTS
        events = _parse_sse_events(response.text)
        error_events = [e for e in events if e["type"] == "RUN_ERROR"]
        assert len(error_events) == 1
        assert "Failed to call a function" in error_events[0]["message"]

    def test_does_not_retry_once_real_content_already_streamed(self, client):
        with chat_agent.override(model=FunctionModel(stream_function=_fail_after_one_chunk_stream_function)):
            response = client.post("/agent", json=_run_agent_input(thread_id="retry-3", content="Find me a sci-fi audiobook"))

        events = _parse_sse_events(response.text)
        event_types = [e["type"] for e in events]
        # The partial text that already reached the client must survive —
        # retrying after commit would duplicate/contradict it, not fix it.
        assert event_types.count("RUN_STARTED") == 1
        text_deltas = "".join(e["delta"] for e in events if e["type"] == "TEXT_MESSAGE_CONTENT")
        assert text_deltas == "Partial"
        assert "RUN_ERROR" in event_types


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

    def test_client_supplied_full_history_is_used_without_any_prior_request(self, client):
        # Tier 5: the client itself resends every prior turn (see
        # app/src/hooks/useAgentStream.ts's entriesToMessages) instead of
        # relying on SessionStore across requests. A brand-new thread that's
        # never hit `/agent` before should still see the full history the
        # client sent in a *single* request.
        with chat_agent.override(model=FunctionModel(stream_function=history_counting_stream_function)):
            response = client.post(
                "/agent",
                json=_run_agent_input_with_messages(
                    thread_id="thread-stateless",
                    messages=[
                        {"role": "user", "content": "turn one"},
                        {"role": "assistant", "content": "reply one"},
                        {"role": "user", "content": "turn two"},
                    ],
                ),
            )

        deltas = "".join(e["delta"] for e in _parse_sse_events(response.text) if e["type"] == "TEXT_MESSAGE_CONTENT")
        assert deltas == "message_count=3"

    def test_multi_message_request_does_not_double_count_history_from_an_earlier_single_message_turn(self, client):
        # A thread starts with the old single-message shape (populating
        # SessionStore), then the client switches to sending its own full
        # history on the next turn. The server must not also prepend
        # SessionStore's copy on top, or the shared turns get counted twice.
        with chat_agent.override(model=FunctionModel(stream_function=history_counting_stream_function)):
            first = client.post("/agent", json=_run_agent_input(thread_id="thread-mixed", content="turn one"))
            assert "".join(
                e["delta"] for e in _parse_sse_events(first.text) if e["type"] == "TEXT_MESSAGE_CONTENT"
            ) == "message_count=1"

            second = client.post(
                "/agent",
                json=_run_agent_input_with_messages(
                    thread_id="thread-mixed",
                    messages=[
                        {"role": "user", "content": "turn one"},
                        {"role": "assistant", "content": "reply one"},
                        {"role": "user", "content": "turn two"},
                    ],
                ),
            )
        deltas = "".join(e["delta"] for e in _parse_sse_events(second.text) if e["type"] == "TEXT_MESSAGE_CONTENT")
        assert deltas == "message_count=3"

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


class TestWidgetRegistrationEnforcement:
    """Tier 6: requests carrying X-LibSync-Library (the embeddable widget's
    frontend, see app/src/hooks/useAgentStream.ts) are checked against the
    registry's allowlist/grace quota — see app/widget_registry.py. Requests
    with no such header (every other test in this file) are untouched."""

    @pytest.fixture(autouse=True)
    def reset_widget_registry(self):
        widget_registry.reset()
        yield
        widget_registry.reset()

    def test_unregistered_widget_traffic_is_allowed_within_its_grace_quota(self, client):
        with chat_agent.override(model=FunctionModel(stream_function=streaming_text_function)):
            response = client.post(
                "/agent",
                json=_run_agent_input(thread_id="widget-grace", content="Hi"),
                headers={"X-LibSync-Library": "new-library", "Origin": "https://new-library.example"},
            )
        assert response.status_code == 200

    def test_unregistered_widget_traffic_is_rejected_once_grace_is_exhausted(self, client):
        origin = "https://abusive-embed.example"
        for _ in range(50):  # GRACE_LIMIT in app/widget_registry.py
            widget_registry.consume_grace(origin)

        response = client.post(
            "/agent",
            json=_run_agent_input(thread_id="widget-grace-exhausted", content="Hi"),
            headers={"X-LibSync-Library": "abusive-library", "Origin": origin},
        )
        assert response.status_code == 403
        assert "grace quota" in response.json()["error"]

    def test_registered_widget_traffic_is_never_grace_limited(self, client):
        origin = "https://acme-library.example"
        widget_registry.register("acme-library", origin)

        with chat_agent.override(model=FunctionModel(stream_function=streaming_text_function)):
            for i in range(5):  # far beyond any small grace quota
                response = client.post(
                    "/agent",
                    json=_run_agent_input(thread_id=f"widget-registered-{i}", content="Hi"),
                    headers={"X-LibSync-Library": "acme-library", "Origin": origin},
                )
                assert response.status_code == 200


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
