"""pydantic-ai Agent setup for the LibSync chat assistant.

Primary models are on Groq (free tier, no card required, rate-limited per
model — see the FallbackModel chain below). Hugging Face Inference Providers
(novita) is the last fallback only, since its free-tier credit ($0.10/mo) is
too small to serve as a primary provider.
"""

import re
from collections.abc import AsyncIterator
from typing import Any

import anyio
import httpx
from ag_ui.core import CustomEvent
from pydantic_ai import Agent, AgentRunResultEvent, ModelRetry, RunContext
from pydantic_ai.messages import PartDeltaEvent, PartStartEvent, TextPart, TextPartDelta, ToolReturn
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.models.huggingface import HuggingFaceModel
from pydantic_ai.providers.groq import GroqProvider
from pydantic_ai.providers.huggingface import HuggingFaceProvider

from app.bot_context.identity import PERSONA_PROMPT
from app.bot_context.service_principles import SERVICE_PRINCIPLES
from app.config import GROQ_API_KEY, HUGGINGFACE_TOKEN
from app.deps import LibSyncDeps
from app.schemas import BookResult, Citation, ResearchResult, ScholarlyWork
from app.services import citation_service, crossref_service, open_library_service, openalex_service
from app.services.pinecone_service import search_pinecone
from app.tenants import policy_namespace
from app.session_store import session_store

# The system prompt provides the AI with its core identity, instructions, and
# knowledge base. It is structured using XML-style tags to create a clear
# hierarchy for the model to follow, and is sent with every user message.
SYSTEM_PROMPT = f"""
<primary_instructions>
{PERSONA_PROMPT}
</primary_instructions>

<guiding_principles>
{SERVICE_PRINCIPLES}
</guiding_principles>

<tool_use>
For any question about this library's own rules, services, or offerings —
fines, lending, renewals, holds, cards, computers, WiFi, printing, rooms,
programs, accessibility, conduct, or anything else the library does — call
`search_library_policies` and ground your answer in what it returns instead
of guessing. Include every specific number it gives (amounts, caps, limits,
time periods), since those are what patrons act on. If it returns nothing
that answers the question, say plainly that you don't have information on
that, suggest asking library staff, and never invent a policy or service.

For any question about a specific book or author — "is X available?", "who
wrote X?", "when did X come out?" — call `search_catalog` and ground your
answer in what it returns. `search_catalog` is backed by the real Open
Library catalog, not by Libby/OverDrive/Kanopy/Hoopla — those platforms have
no public API, so never claim to check them directly or invent availability
for them. If a patron asks about those specific apps, answer from your
general knowledge of how they work, and be clear you can't check real-time
availability there.

Once you have concrete results from `search_catalog`, give your final answer
as structured book data (a short `intro` line plus one entry per book: title,
author, year if known, availability) instead of writing it out as prose —
this lets the UI render real result cards. Use plain text for everything
else: policy answers, general conversation, or when `search_catalog` found
nothing.

For research questions — "find papers on X", "who has written about X",
"what's been cited by/citing this work" — call `search_scholarly_works`
and ground your answer in what it returns. It's backed by the real OpenAlex
scholarly index, not a live citation-analysis tool, so never invent a paper,
author, or citation count it didn't return. A "works that cite this" or
"works this cites" follow-up is the same tool with a query built from the
paper's title/author, since OpenAlex doesn't need a separate lookup step for
that. Summarize what it found in plain text — the result cards render from
the tool's own structured event, not from your reply.

For citation requests — "cite this in APA", "give me an MLA citation for
X" — call `lookup_and_cite` with the style the patron asked for (default to
APA if they didn't say) and a DOI if they gave one, else the title/author.
It resolves the real bibliographic record via Crossref and formats it with
the actual CSL style file, so never hand-format a citation yourself from
memory — citation style rules (et al. thresholds, punctuation, page-range
dashes) are exactly the kind of detail that's wrong more often than it
looks right.
</tool_use>
"""

# Both providers retire model ids without much notice — `llama-3.3-70b-versatile`
# (Groq) and `DeepSeek-V3.2-Exp` (novita) both started 404ing `model_not_found`
# at once, which FallbackModel can't route around since it has nowhere left to
# fall back to. Vet a replacement with `uv run python -m evals.run --model
# groq:<id>` before swapping one in here.
#
# Groq's free tier caps tokens per day *per model* (gpt-oss-120b: 200k, about
# 90 patron turns), so the chain leads with three Groq models — each a
# separate daily quota — before the Hugging Face fallback, whose ~$0.10/month
# credit is a last resort. Ordered by eval pass rate on the 22-case suite
# (October 2026): gpt-oss-120b, then qwen3.8-27b (19/22), then gpt-oss-20b
# (18/22). FallbackModel moves on at any provider error, including a 429.
_groq_provider = GroqProvider(api_key=GROQ_API_KEY)
_groq_model = GroqModel("openai/gpt-oss-120b", provider=_groq_provider)
_groq_qwen_model = GroqModel("qwen/qwen3.8-27b", provider=_groq_provider)
_groq_small_model = GroqModel("openai/gpt-oss-20b", provider=_groq_provider)
_huggingface_model = HuggingFaceModel(
    "deepseek-ai/DeepSeek-V4-Flash",
    provider=HuggingFaceProvider(api_key=HUGGINGFACE_TOKEN, provider_name="novita"),
)
_model = FallbackModel(_groq_model, _groq_qwen_model, _groq_small_model, _huggingface_model)

chat_agent = Agent(
    _model,
    deps_type=LibSyncDeps,
    output_type=str | BookResult,
    system_prompt=SYSTEM_PROMPT,
    retries=5,
    # Recorded on every run's Logfire span, so Tier 8's per-library usage
    # stats (TIER8_PLAN.md §2.3) are a query over existing traces rather
    # than a second logging pipeline.
    metadata=lambda ctx: {"library_id": ctx.deps.library_id or "default"},
)

# Some Llama models served via Groq occasionally leak a tool call into the
# plain-text response instead of issuing a real one, and not in just one
# format — observed variants include `<function=search_catalog{...}`,
# `<search_catalog>{...}</search_catalog>`, and raw
# `{"type": "function", "name": "search_catalog", ...}` JSON. Since `str` is
# a valid final output on its own, the agent would otherwise accept any of
# these as the reply. Retry instead of showing garbled syntax to a patron.
_TOOL_NAMES = ("search_library_policies", "search_catalog", "search_scholarly_works", "lookup_and_cite")
_LEAKED_TOOL_CALL_PATTERN = re.compile(
    r"<function=" r"|<(?:" + "|".join(_TOOL_NAMES) + r")\b" r'|"name"\s*:\s*"(?:' + "|".join(_TOOL_NAMES) + r')"'
)


def _custom_event(name: str, value: dict[str, Any]) -> CustomEvent:
    """Build an AG-UI CUSTOM event for a tool to attach as `ToolReturn.metadata`.

    `AGUIEventStream._handle_tool_result` yields any `BaseEvent` found on
    `ToolReturnPart.metadata` straight into the SSE stream, so this is how a
    tool call turns into a real UI card (book/research/citation) on the
    `/agent` transport instead of prose the model has to narrate.
    """
    return CustomEvent(name=name, value=value)


@chat_agent.output_validator
def _reject_leaked_tool_call_syntax(data: str | BookResult) -> str | BookResult:
    if isinstance(data, str) and _LEAKED_TOOL_CALL_PATTERN.search(data):
        raise ModelRetry(
            "Your previous response leaked raw tool-call syntax into plain text instead of "
            "actually calling the tool. Call the tool properly this time using the real "
            "function-calling mechanism, not text — or if you already have what you need, "
            "answer in plain prose with no function/tool-call syntax of any kind."
        )
    return data


def _search_policies(query: str, library_id: str | None) -> dict:
    # Both calls block on Pinecone, so they run together in one worker thread.
    return search_pinecone(query, 3, namespace=policy_namespace(library_id))


@chat_agent.tool
async def search_library_policies(ctx: RunContext[LibSyncDeps], query: str) -> str:
    """Search the library's policy knowledge base for information relevant to
    the user's question (e.g. fines, lending periods, card registration,
    computer/printing rules, room bookings, conduct, inter-library loan).

    Args:
        query: The patron's question or topic, in plain language.
    """
    try:
        results = await anyio.to_thread.run_sync(_search_policies, query, ctx.deps.library_id)
    except Exception as error:
        print("Policy search error:", error)
        return "Policy lookup is temporarily unavailable."

    matches = [m for m in results.get("matches", []) if m.get("text")]
    if not matches:
        return "No matching library policy was found for that question."
    return "\n".join(f"- {m['text']}" for m in matches)


@chat_agent.tool
async def search_catalog(ctx: RunContext[LibSyncDeps], query: str) -> ToolReturn:
    """Search the real Open Library catalog for a book or author, including
    its lending/full-text availability via Internet Archive.

    Args:
        query: A book title and/or author name, in plain language.
    """
    try:
        results = await open_library_service.search_catalog(ctx.deps.http_client, query, limit=3)
    except Exception as error:
        print("Catalog search error:", error)
        return ToolReturn(return_value="Catalog lookup is temporarily unavailable.")

    if not results:
        return ToolReturn(return_value="No matching titles were found in Open Library.")

    lines = []
    for book in results:
        year = f" ({book['first_publish_year']})" if book.get("first_publish_year") else ""
        lines.append(f'- "{book["title"]}" by {book["author"]}{year} — availability: {book["availability"]}')

    # One CUSTOM event per book (metadata accepts an iterable of BaseEvent,
    # not just one) so cards render live on the AG-UI transport as each
    # result resolves, on top of — not instead of — the structured
    # `BookResult` final-output path that /chat and /chat/stream still use.
    return ToolReturn(
        return_value="\n".join(lines),
        metadata=[_custom_event("book_card", book) for book in results],
    )


@chat_agent.tool
async def search_scholarly_works(ctx: RunContext[LibSyncDeps], query: str) -> ToolReturn:
    """Search the real OpenAlex scholarly index for papers matching a topic
    or title, including citation counts and open-access status.

    Args:
        query: A research topic or paper title, in plain language.
    """
    try:
        results = await openalex_service.search_scholarly_works(ctx.deps.http_client, query, limit=5)
    except Exception as error:
        print("OpenAlex search error:", error)
        return ToolReturn(return_value="Scholarly search is temporarily unavailable.")

    if not results:
        return ToolReturn(return_value="No matching scholarly works were found on OpenAlex.")

    lines = []
    for work in results:
        year = f" ({work['year']})" if work.get("year") else ""
        oa = "open access" if work["is_oa"] else "not open access"
        lines.append(f'- "{work["title"]}" by {work["authors"]}{year} — {work["citation_count"]} citations, {oa}')

    payload = ResearchResult(
        intro=f'Found {len(results)} work(s) for "{query}":',
        works=[ScholarlyWork(**work) for work in results],
    )
    return ToolReturn(
        return_value="\n".join(lines),
        metadata=_custom_event("research_results", payload.model_dump()),
    )


@chat_agent.tool
async def lookup_and_cite(
    ctx: RunContext[LibSyncDeps], style: str, doi: str | None = None, title: str | None = None
) -> ToolReturn:
    """Look up a work's real bibliographic record — via DOI if the patron
    has one, else a title/author search — and format it as a citation in
    the requested style, using the real CSL style file rather than
    hand-formatting from memory.

    Args:
        style: Citation style — one of "apa", "mla", "chicago".
        doi: The work's DOI, if the patron provided one.
        title: The work's title (and author, if known), if no DOI was given.
    """
    style = style.strip().lower()
    if style not in citation_service.STYLE_FILES:
        supported = ", ".join(sorted(citation_service.STYLE_FILES))
        return ToolReturn(return_value=f"Unsupported citation style '{style}'. Supported styles: {supported}.")
    if not doi and not title:
        return ToolReturn(return_value="I need either a DOI or a title to look up a citation.")

    try:
        work = await crossref_service.lookup_work(ctx.deps.http_client, doi=doi, title=title)
    except Exception as error:
        print("Crossref lookup error:", error)
        return ToolReturn(return_value="Citation lookup is temporarily unavailable.")

    if work is None:
        return ToolReturn(return_value="No matching work was found on Crossref for that citation request.")

    try:
        formatted = citation_service.format_citation(work, style)
    except Exception as error:
        print("Citation formatting error:", error)
        return ToolReturn(return_value="Found the work on Crossref, but formatting the citation failed.")

    payload = Citation(
        formatted=formatted,
        style=style,
        doi=work.get("DOI"),
        available_styles=sorted(citation_service.STYLE_FILES),
    )
    return ToolReturn(
        return_value=formatted,
        metadata=_custom_event("citation", payload.model_dump()),
    )


async def get_chat_reply(
    message: str, http_client: httpx.AsyncClient, session_id: str, library_id: str | None = None
) -> str | BookResult:
    """Send a user's message to the chat agent and return its reply — plain
    text, or a `BookResult` when the agent grounds its answer in concrete
    `search_catalog` results.

    Conversation history for `session_id` (if any) is passed to the agent as
    `message_history`, and the new turn is appended back to the session store
    afterward, so multi-turn conversations stay coherent within a session.

    Raises:
        RuntimeError: If the underlying model call fails.
    """
    try:
        print("Received message:", message)
        deps = LibSyncDeps(http_client=http_client, library_id=library_id)
        history = session_store.get(session_id)
        result = await chat_agent.run(message, deps=deps, message_history=history)
        session_store.append(session_id, result.new_messages())
        print("Agent reply:", result.output)
        return result.output
    except Exception as error:
        print("Agent error:", error)
        raise RuntimeError(
            "⚠️ Error: Unable to reach AI service. Please try again later."
        ) from error


async def stream_chat_reply(
    message: str, http_client: httpx.AsyncClient, session_id: str, library_id: str | None = None
) -> AsyncIterator[tuple[str, dict]]:
    """Stream a chat turn as `(event_name, data)` pairs for SSE delivery.

    Opens the model connection and starts yielding immediately, rather than
    waiting for the full reply — this is what actually offsets Render's cold
    start, since the browser sees activity right away instead of a blank
    spinner for up to ~50s.

    Built on `run_stream_events()` (which wraps `run()`), not the simpler
    `run_stream()` — `run_stream()` commits to the first content matching
    `output_type` and won't execute any tool call that follows it in the same
    turn. Since `str` is a valid output on its own, a model that narrates
    ("I'll check the catalog...") before its tool call would have that
    narration treated as the final answer and the tool call silently
    dropped. `run_stream_events()` runs the full graph, so the tool call
    after the narration still executes; observed live against Groq.

    Events: "text" (cumulative text of whichever text part is currently
    streaming — resets, rather than appends, when a new text part starts, so
    e.g. "I'll check the catalog..." is replaced by the grounded answer that
    follows it instead of both being concatenated), "books" (the final
    `BookResult`, sent once, complete, when the turn resolves to one), "done"
    once the turn is complete and saved to the session store, or "error".
    """
    deps = LibSyncDeps(http_client=http_client, library_id=library_id)
    history = session_store.get(session_id)
    try:
        current_text: str | None = None
        async with chat_agent.run_stream_events(message, deps=deps, message_history=history) as events:
            async for event in events:
                if isinstance(event, PartStartEvent) and isinstance(event.part, TextPart):
                    current_text = event.part.content
                    if current_text:
                        yield ("text", {"text": current_text})
                elif isinstance(event, PartDeltaEvent) and isinstance(event.delta, TextPartDelta):
                    if current_text is not None:
                        current_text += event.delta.content_delta
                        yield ("text", {"text": current_text})
                elif isinstance(event, AgentRunResultEvent):
                    if isinstance(event.result.output, BookResult):
                        yield ("books", event.result.output.model_dump())
                    session_store.append(session_id, event.result.new_messages())
        yield ("done", {})
    except Exception as error:
        print("Streaming agent error:", error)
        yield ("error", {"error": "⚠️ Error: Unable to reach AI service. Please try again later."})
