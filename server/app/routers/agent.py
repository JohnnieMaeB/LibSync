"""Route for the AG-UI protocol transport (`/agent`) — the Tier 2 interactive UI.

Uses AGUIAdapter's composable pieces (`from_request` + `run_stream` +
`streaming_response`) rather than the all-in-one `dispatch_request`
classmethod, so conversation history keeps coming from the existing
`SessionStore`, keyed by the AG-UI thread id instead of a bespoke session id.
`/chat` and `/chat/stream` (see chat.py) are untouched and stay available as
a fallback transport.

Tier 5 clients (see app/src/hooks/useAgentStream.ts's `entriesToMessages`)
resend the whole conversation's turns on every request instead of just the
newest message — `SessionStore` then stops being load-bearing for those
requests (see `_message_history_for` below), though it's still populated as
a bounded fallback for callers that only ever send the latest message (older
clients, and this endpoint's own tests).
"""

import uuid
from collections.abc import AsyncIterator
from typing import Any

from ag_ui.core import BaseEvent, EventType, RunErrorEvent
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.ui.ag_ui import AGUIAdapter

from app.agent import chat_agent
from app.deps import LibSyncDeps
from app.rate_limit import RATE_LIMIT, limiter
from app.services import citation_service, crossref_service
from app.session_store import session_store

router = APIRouter()

# Groq's `llama-3.3-70b-versatile` occasionally rejects its own tool-call
# generation as `tool_use_failed` mid-stream (observed live at roughly a
# 2-in-3 failure rate for some prompts, e.g. "Find me a sci-fi audiobook").
# pydantic-ai's own recovery for this (GroqStreamedResponse._get_event_iterator
# in pydantic_ai/models/groq.py) only covers the case where Groq's error body
# matches its expected schema; when it doesn't, the raw provider exception
# propagates past FallbackModel's boundary — which only guards stream *entry*,
# not iteration of an already-entered stream — straight to the AG-UI
# adapter's on_error handler, surfacing Groq's raw error text ("Failed to
# call a function...") to the patron instead of a retry or an HF fallback.
_MAX_AGENT_RUN_ATTEMPTS = 3
# Events safe to discard and replay on retry — nothing has reached the
# client yet. Once any other event type streams, the response is committed
# and can no longer be silently retried.
_PRE_COMMIT_EVENT_TYPES = frozenset({EventType.RUN_STARTED})


async def _run_stream_with_retry(adapter: AGUIAdapter, **run_kwargs: Any) -> AsyncIterator[BaseEvent]:
    """Retries a whole agent turn if it fails before any real content streamed.

    Safe to retry specifically because this failure mode happens before any
    TEXT_MESSAGE_*/TOOL_CALL_*/CUSTOM event — nothing has reached the client
    yet to duplicate or contradict — and `on_complete` (session persistence)
    only fires when a run completes successfully, so a discarded attempt is
    never persisted twice, or at all.
    """
    last_error_event: RunErrorEvent | None = None
    for attempt in range(1, _MAX_AGENT_RUN_ATTEMPTS + 1):
        buffered: list[BaseEvent] = []
        committed = False
        try:
            async for event in adapter.run_stream(**run_kwargs):
                if not committed:
                    if isinstance(event, RunErrorEvent):
                        last_error_event = event
                        break
                    if event.type in _PRE_COMMIT_EVENT_TYPES:
                        buffered.append(event)
                        continue
                    committed = True
                    for buffered_event in buffered:
                        yield buffered_event
                    buffered.clear()
                yield event
            else:
                return
            if committed:
                return
        except Exception as error:  # defensive: on_error already converts run failures into RunErrorEvent
            # Never retry once committed — real content already reached the
            # client, and re-running would duplicate or contradict it.
            if committed or attempt == _MAX_AGENT_RUN_ATTEMPTS:
                raise
            print(f"Agent run attempt {attempt} raised, retrying:", error)
            continue
    if last_error_event is not None:
        yield last_error_event


@router.post("/agent")
@limiter.limit(RATE_LIMIT)
async def agent_endpoint(request: Request):
    adapter = await AGUIAdapter.from_request(request, agent=chat_agent)
    thread_id = adapter.conversation_id or str(uuid.uuid4())
    deps = LibSyncDeps(http_client=request.app.state.http_client)

    # AGUIAdapter.run_stream_native folds the frontend's sent messages onto
    # the end of whatever `message_history` we pass it. A single-message
    # request (today's pre-Tier-5 shape) needs SessionStore's prior turns
    # prepended, or the model only ever sees the latest question. A
    # multi-message request already *is* the full history the client is
    # tracking, so prepending SessionStore's copy on top would duplicate
    # every earlier turn — pass no server-side history for those.
    history = session_store.get(thread_id) if len(adapter.run_input.messages) <= 1 else []

    def _persist(result: AgentRunResult) -> None:
        # `result.new_messages()` only covers what the run generated *beyond*
        # the `message_history` it was given — and AGUIAdapter folds this
        # request's frontend-sent turn(s) into that same `message_history`
        # before running, so they never show up in `new_messages()`. Replace
        # (not append to) the stored session with `history + this request's
        # frontend messages + the run's new messages` — the full, correct
        # transcript either way: for a single-message request this equals
        # what the old `append`-based logic produced; for a multi-message
        # request it avoids re-appending turns the client already included
        # in `history` on some earlier request.
        frontend_messages = adapter.sanitize_messages(
            adapter.messages, deferred_tool_results=adapter.deferred_tool_results
        )
        session_store.set(thread_id, [*history, *frontend_messages, *result.new_messages()])

    return adapter.streaming_response(
        _run_stream_with_retry(
            adapter,
            message_history=history,
            deps=deps,
            conversation_id=thread_id,
            on_complete=_persist,
        )
    )


@router.get("/citation/{doi:path}")
@limiter.limit(RATE_LIMIT)
async def citation_style_switch(request: Request, doi: str, style: str = "apa"):
    """Re-formats an already-resolved citation in a different style without
    a fresh Crossref lookup, for the citation card's style switcher —
    `crossref_service.lookup_work` serves this from its short-lived cache
    when the DOI was already resolved this turn by `lookup_and_cite`."""
    style = style.strip().lower()
    if style not in citation_service.STYLE_FILES:
        supported = ", ".join(sorted(citation_service.STYLE_FILES))
        return JSONResponse(status_code=400, content={"error": f"Unsupported style '{style}'. Supported: {supported}."})

    try:
        work = await crossref_service.lookup_work(request.app.state.http_client, doi=doi)
    except Exception:
        return JSONResponse(status_code=502, content={"error": "Citation lookup is temporarily unavailable."})

    if work is None:
        return JSONResponse(status_code=404, content={"error": "No matching work was found on Crossref for that DOI."})

    formatted = citation_service.format_citation(work, style)
    return {
        "formatted": formatted,
        "style": style,
        "doi": work.get("DOI"),
        "available_styles": sorted(citation_service.STYLE_FILES),
    }
