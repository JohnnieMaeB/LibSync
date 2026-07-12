"""Route for the AG-UI protocol transport (`/agent`) — the Tier 2 interactive UI.

Uses AGUIAdapter's composable pieces (`from_request` + `run_stream` +
`streaming_response`) rather than the all-in-one `dispatch_request`
classmethod, so conversation history keeps coming from the existing
`SessionStore`, keyed by the AG-UI thread id instead of a bespoke session id.
`/chat` and `/chat/stream` (see chat.py) are untouched and stay available as
a fallback transport.
"""

import uuid

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


@router.post("/agent")
@limiter.limit(RATE_LIMIT)
async def agent_endpoint(request: Request):
    adapter = await AGUIAdapter.from_request(request, agent=chat_agent)
    thread_id = adapter.conversation_id or str(uuid.uuid4())
    deps = LibSyncDeps(http_client=request.app.state.http_client)
    history = session_store.get(thread_id)

    def _persist(result: AgentRunResult) -> None:
        # `result.new_messages()` only covers what the run generated *beyond*
        # the `message_history` it was given — and AGUIAdapter folds this
        # request's frontend-sent turn (the new user message) into that same
        # `message_history` before running, so it never shows up in
        # `new_messages()`. Persist the frontend's turn alongside the run's
        # new messages, or each saved turn loses its own user prompt and the
        # next turn's model call sees a broken (response-only) transcript.
        frontend_messages = adapter.sanitize_messages(
            adapter.messages, deferred_tool_results=adapter.deferred_tool_results
        )
        session_store.append(thread_id, [*frontend_messages, *result.new_messages()])

    return adapter.streaming_response(
        adapter.run_stream(
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
