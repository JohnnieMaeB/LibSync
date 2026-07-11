"""pydantic-ai Agent setup for the LibSync chat assistant.

Primary model is Groq (free tier: 30 RPM / 14,400 req/day, no card required).
Hugging Face Inference Providers (novita) is wired as a fallback only, since
its free-tier credit ($0.10/mo) is too small to serve as a primary provider.
"""

import re
from collections.abc import AsyncIterator

import anyio
import httpx
from pydantic_ai import Agent, AgentRunResultEvent, ModelRetry, RunContext
from pydantic_ai.messages import PartDeltaEvent, PartStartEvent, TextPart, TextPartDelta
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.models.huggingface import HuggingFaceModel
from pydantic_ai.providers.groq import GroqProvider
from pydantic_ai.providers.huggingface import HuggingFaceProvider

from app.bot_context.bill_of_rights import ALA_BILL_OF_RIGHTS
from app.bot_context.core_values import ALA_CORE_VALUES
from app.bot_context.identity import PERSONA_PROMPT
from app.bot_context.rusa_guidelines import RUSA_GUIDELINES
from app.config import GROQ_API_KEY, HUGGINGFACE_TOKEN
from app.deps import LibSyncDeps
from app.schemas import BookResult
from app.services import open_library_service
from app.services.pinecone_service import search_pinecone
from app.session_store import session_store

# The system prompt provides the AI with its core identity, instructions, and
# knowledge base. It is structured using XML-style tags to create a clear
# hierarchy for the model to follow, and is sent with every user message.
SYSTEM_PROMPT = f"""
<primary_instructions>
{PERSONA_PROMPT}
</primary_instructions>

<guiding_principles>
<knowledge_source name="RUSA Guidelines for Behavioral Performance">
{RUSA_GUIDELINES}
</knowledge_source>

<knowledge_source name="ALA Library Bill of Rights">
{ALA_BILL_OF_RIGHTS}
</knowledge_source>

<knowledge_source name="ALA Core Values of Librarianship">
{ALA_CORE_VALUES}
</knowledge_source>

</guiding_principles>

<tool_use>
For any question about concrete library policy — fines, lending periods, card
registration, computer/printing rules, room bookings, conduct, or similar —
call `search_library_policies` and ground your answer in what it returns
instead of guessing. If it returns nothing relevant, say so rather than
inventing a policy.

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
</tool_use>
"""

_groq_model = GroqModel(
    "llama-3.3-70b-versatile",
    provider=GroqProvider(api_key=GROQ_API_KEY),
)
_huggingface_model = HuggingFaceModel(
    "deepseek-ai/DeepSeek-V3.2-Exp",
    provider=HuggingFaceProvider(api_key=HUGGINGFACE_TOKEN, provider_name="novita"),
)
_model = FallbackModel(_groq_model, _huggingface_model)

chat_agent = Agent(
    _model, deps_type=LibSyncDeps, output_type=str | BookResult, system_prompt=SYSTEM_PROMPT, retries=5
)

# Some Llama models served via Groq occasionally leak a tool call into the
# plain-text response instead of issuing a real one, and not in just one
# format — observed variants include `<function=search_catalog{...}`,
# `<search_catalog>{...}</search_catalog>`, and raw
# `{"type": "function", "name": "search_catalog", ...}` JSON. Since `str` is
# a valid final output on its own, the agent would otherwise accept any of
# these as the reply. Retry instead of showing garbled syntax to a patron.
_TOOL_NAMES = ("search_library_policies", "search_catalog")
_LEAKED_TOOL_CALL_PATTERN = re.compile(
    r"<function=" r"|<(?:" + "|".join(_TOOL_NAMES) + r")\b" r'|"name"\s*:\s*"(?:' + "|".join(_TOOL_NAMES) + r')"'
)


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


@chat_agent.tool_plain
async def search_library_policies(query: str) -> str:
    """Search the library's policy knowledge base for information relevant to
    the user's question (e.g. fines, lending periods, card registration,
    computer/printing rules, room bookings, conduct, inter-library loan).

    Args:
        query: The patron's question or topic, in plain language.
    """
    try:
        results = await anyio.to_thread.run_sync(search_pinecone, query, 3)
    except Exception as error:
        print("Policy search error:", error)
        return "Policy lookup is temporarily unavailable."

    matches = [m for m in results.get("matches", []) if m.get("text")]
    if not matches:
        return "No matching library policy was found for that question."
    return "\n".join(f"- {m['text']}" for m in matches)


@chat_agent.tool
async def search_catalog(ctx: RunContext[LibSyncDeps], query: str) -> str:
    """Search the real Open Library catalog for a book or author, including
    its lending/full-text availability via Internet Archive.

    Args:
        query: A book title and/or author name, in plain language.
    """
    try:
        results = await open_library_service.search_catalog(ctx.deps.http_client, query, limit=3)
    except Exception as error:
        print("Catalog search error:", error)
        return "Catalog lookup is temporarily unavailable."

    if not results:
        return "No matching titles were found in Open Library."

    lines = []
    for book in results:
        year = f" ({book['first_publish_year']})" if book.get("first_publish_year") else ""
        lines.append(f'- "{book["title"]}" by {book["author"]}{year} — availability: {book["availability"]}')
    return "\n".join(lines)


async def get_chat_reply(message: str, http_client: httpx.AsyncClient, session_id: str) -> str | BookResult:
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
        deps = LibSyncDeps(http_client=http_client)
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
    message: str, http_client: httpx.AsyncClient, session_id: str
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
    deps = LibSyncDeps(http_client=http_client)
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
