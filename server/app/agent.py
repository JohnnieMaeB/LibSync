"""pydantic-ai Agent setup for the LibSync chat assistant.

Primary models are on Groq (free tier, no card required, rate-limited per
model — see the FallbackModel chain below). Hugging Face Inference Providers
(novita) is the last fallback only, since its free-tier credit ($0.10/mo) is
too small to serve as a primary provider.
"""

import re
from collections.abc import AsyncIterator
from typing import Any, Literal

import anyio
import httpx
from ag_ui.core import CustomEvent
from pydantic_ai import Agent, AgentRunResultEvent, ModelRetry, RunContext
from pydantic_ai.messages import (
    PartDeltaEvent,
    PartStartEvent,
    TextPart,
    TextPartDelta,
    ToolReturn,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.models.huggingface import HuggingFaceModel
from pydantic_ai.providers.groq import GroqProvider
from pydantic_ai.providers.huggingface import HuggingFaceProvider
from pydantic_ai.tools import ToolDefinition

from app.bot_context.identity import PERSONA_PROMPT
from app.bot_context.service_principles import SERVICE_PRINCIPLES
from app.config import GROQ_API_KEY, HUGGINGFACE_TOKEN
from app.deps import LibSyncDeps
from app.schemas import CATALOG_BOOKS_CONTEXT, BookResult, Citation, ResearchResult, ScholarlyWork
from app.library_config import LibraryConfig
from app.grounding import unsupported_quantities
from app.library_config import get_library_secret
from app import capacity
from app.services import (
    catalog,
    citation_service,
    crossref_service,
    libcal,
    openalex_service,
    overdrive,
    readers_advisory,
)
from app.services.sip2 import SIP2Client
from app.services.pinecone_service import search_pinecone
from app.tenants import TOOL_GROUPS, policy_namespace
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
time periods), since those are what patrons act on, and when a policy lists
several prices or tiers (for example black-and-white and color copies), give
every one. If it returns nothing
that answers the question, say plainly that you don't have information on
that, suggest asking library staff, and never invent a policy or service.
Say only what the policy text says: no numbers, services, steps, exceptions
or "usually" qualifiers it doesn't contain. If a patron asks about something
the policy leaves out (for example, whether a renewal can be done in person),
say the policy doesn't cover it.

For any question about a specific book or author — "is X available?", "who
wrote X?", "when did X come out?" — call `search_catalog` and ground your
answer in what it returns. `search_catalog` searches this library's own
catalog when it's connected, and the real Open Library catalog otherwise
(its result says which); it is not backed by Libby/OverDrive/Kanopy/Hoopla — those platforms have
no public API, so never claim to check them directly or invent availability
for them. If a patron asks about those specific apps, answer from your
general knowledge of how they work, and be clear you can't check real-time
availability there.

Once you have concrete results from `search_catalog`, give your final answer
as structured book data (a short `intro` line plus one entry per book: title,
author, year if known, availability) instead of writing it out as prose —
this lets the UI render real result cards. Use plain text for everything
else: policy answers, general conversation, or when `search_catalog` found
nothing. The exception: if the patron is asking whether a book is available
on Libby, OverDrive, Kanopy, hoopla, or any other platform you can't check,
answer in plain text instead of cards: say plainly that you can't see live
availability there, share what the catalog did show, and tell them how to
check in that app.

For recommendations — "books like X", "something for a 10-year-old who loves
dragons", "what should I read next?" — call `recommend_books` and suggest only
the books it returns, as structured book data like a catalog answer. Never
recommend a title from memory: it may not exist or not be in this library.
If it returns nothing, say so and offer to search for a specific title.

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

In every answer, never say this library has a particular database,
subscription, app, website feature, or service (for example EBSCOhost,
JSTOR, RefWorks, a mobile app, free interlibrary loan) unless a tool result
this conversation says so. You don't know what this library subscribes to.
When it would help, say such things exist at many libraries and suggest
asking library staff what this one offers.
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
# Its own HTTP client so every Groq response's rate-limit headers reach
# app/capacity.py (the dashboard's capacity view). Timeouts match the client
# pydantic-ai would otherwise create.
_groq_provider = GroqProvider(
    api_key=GROQ_API_KEY,
    http_client=httpx.AsyncClient(
        timeout=httpx.Timeout(timeout=600, connect=5), event_hooks={"response": [capacity.on_response]}
    ),
)
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
    # Grounds structured book answers in the catalog's own results, via a
    # Pydantic validator on BookResult. A lambda, so the helper (defined
    # further down, after the tools) is looked up at validation time.
    validation_context=lambda ctx: _validation_context(ctx),
)

# Some Llama models served via Groq occasionally leak a tool call into the
# plain-text response instead of issuing a real one, and not in just one
# format — observed variants include `<function=search_catalog{...}`,
# `<search_catalog>{...}</search_catalog>`, and raw
# `{"type": "function", "name": "search_catalog", ...}` JSON. Since `str` is
# a valid final output on its own, the agent would otherwise accept any of
# these as the reply. Retry instead of showing garbled syntax to a patron.
_TOOL_NAMES = (
    "search_library_policies",
    "search_catalog",
    "recommend_books",
    "search_scholarly_works",
    "lookup_and_cite",
    "check_ebook_availability",
    "check_room_availability",
    "check_library_events",
    "check_my_account",
)
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


# How many times the model may rephrase a policy answer before the patron gets
# the policy text itself (grounded by construction) instead of an error.
POLICY_GROUNDING_RETRIES = 2


def _policy_turn_sources(messages) -> tuple[list[str], list[str]]:
    """(policy text returned in the current turn, every tool result and patron
    message in the conversation). The first decides whether the check applies;
    the second is what a number in the answer may come from."""
    last_prompt = max(
        (i for i, m in enumerate(messages) for p in getattr(m, "parts", []) if isinstance(p, UserPromptPart)),
        default=-1,
    )
    policy_now: list[str] = []
    sources: list[str] = []
    for index, message in enumerate(messages):
        for part in getattr(message, "parts", []):
            if isinstance(part, ToolReturnPart):
                content = part.content if isinstance(part.content, str) else str(part.content)
                sources.append(content)
                if part.tool_name == "search_library_policies" and index > last_prompt:
                    policy_now.append(content)
            elif isinstance(part, UserPromptPart):
                sources.append(part.content if isinstance(part.content, str) else str(part.content))
    return policy_now, sources


@chat_agent.output_validator
def _ground_policy_numbers(ctx: RunContext[LibSyncDeps], data: str | BookResult) -> str | BookResult:
    """Every number in a policy answer must come from what the policy search
    returned (NEXT_FEATURES.md P0.1; app/grounding.py). On a miss the model is
    told exactly which number and retries; if it still can't, the patron gets
    the retrieved policy text verbatim rather than a wrong number or an error."""
    if not isinstance(data, str):
        return data
    policy_now, sources = _policy_turn_sources(ctx.messages)
    if not policy_now:
        return data
    unsupported = unsupported_quantities(data, sources)
    if not unsupported:
        return data
    if ctx.retry < POLICY_GROUNDING_RETRIES:
        raise ModelRetry(
            f"Your answer states {', '.join(repr(q) for q in unsupported)}, which isn't in the library policy text "
            "you retrieved. Only state numbers (amounts, limits, time periods, counts) that the policy gives. If the "
            "policy doesn't say, tell the patron that and suggest asking library staff."
        )
    print("Policy answer fell back to verbatim policy text; unsupported:", unsupported)
    return (
        "Here's what the library's policy says:\n\n"
        + "\n".join(policy_now)
        + "\n\nFor anything the policy doesn't cover, please ask library staff."
    )


_BOOK_TOOLS = ("search_catalog", "recommend_books")


def _catalog_books_seen(messages) -> dict[str, dict]:
    """Every book `search_catalog` or `recommend_books` returned this run,
    keyed by folded title, read from the book_card events attached to their
    tool returns."""
    seen: dict[str, dict] = {}
    for message in messages:
        for part in getattr(message, "parts", []):
            if not isinstance(part, ToolReturnPart) or part.tool_name not in _BOOK_TOOLS:
                continue
            events = part.metadata if isinstance(part.metadata, list) else [part.metadata]
            for event in events:
                if isinstance(event, CustomEvent) and event.name == "book_card":
                    seen.setdefault(event.value["title"].casefold().strip(), event.value)
    return seen


def _validation_context(ctx: RunContext[LibSyncDeps]) -> dict:
    """Pydantic validation context for structured outputs. pydantic-ai rebuilds
    it at every step, so by the time the final BookResult is validated it holds
    every book `search_catalog` returned this run (schemas.BookResult)."""
    return {CATALOG_BOOKS_CONTEXT: _catalog_books_seen(ctx.messages)}


def _tool_group_switch(group: str):
    """A `prepare` hook that hides a tool from the model when the embedding
    library switched its group off (TIER8_PLAN.md §2.8). Hidden, not refused:
    the model never sees the tool, so it can't promise a lookup it can't do."""
    assert group in TOOL_GROUPS

    async def prepare(ctx: RunContext[LibSyncDeps], tool_def: ToolDefinition) -> ToolDefinition | None:
        enabled = ctx.deps.enabled_tools
        return tool_def if enabled is None or group in enabled else None

    return prepare


def _search_policies(query: str, library_id: str | None) -> dict:
    # Both calls block on Pinecone, so they run together in one worker thread.
    return search_pinecone(query, 3, namespace=policy_namespace(library_id))


@chat_agent.tool(prepare=_tool_group_switch("policies"))
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


@chat_agent.tool(prepare=_tool_group_switch("catalog"))
async def search_catalog(ctx: RunContext[LibSyncDeps], query: str) -> ToolReturn:
    """Search for a book or author in this library's own catalog when one is
    connected (Tier 8 Phase 32), otherwise the real Open Library catalog,
    including availability.

    Args:
        query: A book title and/or author name, in plain language.
    """
    try:
        search = await catalog.search_catalog(ctx.deps.http_client, ctx.deps.library_config, query, limit=3)
    except Exception as error:
        print("Catalog search error:", error)
        return ToolReturn(return_value="Catalog lookup is temporarily unavailable.")

    results = search.results
    if not results:
        return ToolReturn(return_value=f"No matching titles were found in {search.source}.")

    lines = [f"Results from {search.source}:"]
    if search.fell_back:
        lines.insert(
            0,
            "Note: the library's own catalog didn't respond, so these come from Open Library and don't show "
            "this library's copies. Tell the patron that.",
        )
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


@chat_agent.tool(prepare=_tool_group_switch("recommendations"))
async def recommend_books(
    ctx: RunContext[LibSyncDeps],
    like: str | None = None,
    about: str | None = None,
    audience: Literal["children", "teen", "adult"] | None = None,
) -> ToolReturn:
    """Recommend books (readers' advisory): read-alikes for a book the patron
    enjoyed, or books on a topic, held by this library when its catalog is
    connected. Suggest only what this returns.

    Args:
        like: A book (title and author if known) the patron wants more like.
        about: A topic or theme, in a few words (e.g. "dragons", "climate fiction").
        audience: Who the books are for: "children" (up to about 12), "teen", or
            "adult". Always set it when the patron mentions a child, an age or a
            grade.
    """
    if not like and not about:
        return ToolReturn(return_value="Ask the patron for a book they enjoyed or a topic they'd like.")
    try:
        books, source, subjects = await readers_advisory.recommend(
            ctx.deps.http_client, ctx.deps.library_config, like=like, about=about, audience=audience
        )
    except Exception as error:
        print("Recommendation error:", type(error).__name__, error)
        return ToolReturn(return_value="Recommendations are temporarily unavailable.")
    if not books:
        return ToolReturn(return_value=f"No recommendations were found in {source}.")

    lines = [f"Recommendations from {source}, sharing the subjects: {', '.join(subjects) or about}."]
    for book in books:
        year = f" ({book['first_publish_year']})" if book.get("first_publish_year") else ""
        lines.append(f'- "{book["title"]}" by {book["author"]}{year} — availability: {book["availability"]}')
    return ToolReturn(
        return_value="\n".join(lines),
        metadata=[_custom_event("book_card", book) for book in books],
    )


@chat_agent.instructions
def _library_instructions(ctx: RunContext[LibSyncDeps]) -> str | None:
    """Per-library guidance (Phases 30, 37T), added only for what the library
    configured, so every other library gets exactly the static prompt."""
    config = ctx.deps.library_config
    if config is None:
        return None
    lines = []
    if config.help_url:
        lines.append(
            "If you can't answer, the patron needs something only staff can do, or they ask for a person, "
            f"give them this way to reach library staff: {config.help_url}"
        )
    if config.integration("overdrive"):
        lines.append(
            "This library's OverDrive/Libby collection is connected: for Libby or OverDrive e-book and audiobook "
            "questions, call `check_ebook_availability` and report its live copy and hold counts instead of saying "
            "you can't check Libby."
        )
    patron = ctx.deps.patron
    if patron is not None and patron.kind == "card" and config.integration("sip2"):
        lines.append(
            "The patron is signed in with their library card. For questions about their own checkouts, due dates, "
            "holds or fees, call `check_my_account`; it shows them the titles directly, so only discuss the counts."
        )
    if config.integration("libcal"):
        lines.append(
            "For questions about free study or meeting rooms on a date, call `check_room_availability` and point "
            "the patron to the booking link it returns; you can't book rooms yourself."
        )
        if config.integration("libcal").get("calendar_id"):
            lines.append(
                "For questions about events, programs, classes or storytimes, call `check_library_events` and "
                "mention only events it returns, with their dates and registration links; you can't register "
                "patrons yourself."
            )
    return "\n".join(lines) or None


def _when_configured(group: str, integration: str):
    """Hidden unless the library set up this vendor and hasn't switched the group off."""
    switch = _tool_group_switch(group)

    async def prepare(ctx: RunContext[LibSyncDeps], tool_def: ToolDefinition) -> ToolDefinition | None:
        config = ctx.deps.library_config
        if config is None or not config.integration(integration):
            return None
        return await switch(ctx, tool_def)

    return prepare


@chat_agent.tool(prepare=_when_configured("ebooks", "overdrive"))
async def check_ebook_availability(ctx: RunContext[LibSyncDeps], query: str) -> str:
    """Check live availability of an e-book or audiobook in this library's
    OverDrive/Libby collection: copies available, copies owned, and holds.

    Args:
        query: A title and/or author.
    """
    config = ctx.deps.library_config
    try:
        secret = await get_library_secret(ctx.deps.http_client, config.id, "overdrive_client_secret")
        results = await overdrive.search_availability(
            ctx.deps.http_client, config.integration("overdrive"), secret, query
        )
    except Exception as error:
        print("OverDrive lookup failed:", error)
        return "Libby/OverDrive availability is temporarily unavailable. Suggest checking in the Libby app."
    if not results:
        return "No matching titles were found in this library's Libby/OverDrive collection."
    lines = []
    for item in results:
        by = f" by {item['creator']}" if item.get("creator") else ""
        formats = f" ({', '.join(item['formats'])})" if item.get("formats") else ""
        counts = (
            f"{item['copies_available']} of {item['copies_owned']} copies available, {item['holds']} holds"
            if item.get("copies_owned") is not None
            else "availability unknown"
        )
        lines.append(f'- "{item["title"]}"{by}{formats}: {counts}')
    return "Live availability in this library's Libby/OverDrive collection:\n" + "\n".join(lines)


@chat_agent.tool(prepare=_when_configured("rooms", "libcal"))
async def check_room_availability(ctx: RunContext[LibSyncDeps], date: str) -> str:
    """List which of the library's study or meeting rooms are free on a date
    (read-only; booking happens on the library's LibCal page).

    Args:
        date: The day to check, as YYYY-MM-DD.
    """
    config = ctx.deps.library_config
    settings = config.integration("libcal")
    try:
        secret = await get_library_secret(ctx.deps.http_client, config.id, "libcal_client_secret")
        rooms = await libcal.room_availability(ctx.deps.http_client, settings, secret, date)
    except Exception as error:
        print("LibCal lookup failed:", error)
        return "Room availability is temporarily unavailable."
    booking = settings.get("booking_url")
    footer = f"\nBook at: {booking}" if booking else ""
    if not rooms:
        return f"No rooms were listed for {date}.{footer}"
    lines = [
        f"- {room['name']}" + (f" (seats {room['capacity']})" if room.get("capacity") else "") + ": "
        + (", ".join(room["free"]) if room["free"] else "no free times")
        for room in rooms
    ]
    return f"Free times on {date}:\n" + "\n".join(lines) + footer


async def _when_signed_in_with_card(ctx: RunContext[LibSyncDeps], tool_def: ToolDefinition) -> ToolDefinition | None:
    """Only for a patron signed in with their card, at a library with SIP2,
    unless the library switched the "account" group off (Tier 9 Phase 38)."""
    patron, config = ctx.deps.patron, ctx.deps.library_config
    if patron is None or patron.kind != "card" or not patron.card or config is None or not config.integration("sip2"):
        return None
    return await _tool_group_switch("account")(ctx, tool_def)



def _events_configured():
    """Hidden unless LibCal is set up with an events calendar and the library
    hasn't switched events off."""
    base = _when_configured("events", "libcal")

    async def prepare(ctx: RunContext[LibSyncDeps], tool_def: ToolDefinition) -> ToolDefinition | None:
        config = ctx.deps.library_config
        if config is None or not (config.integration("libcal") or {}).get("calendar_id"):
            return None
        return await base(ctx, tool_def)

    return prepare


@chat_agent.tool(prepare=_events_configured())
async def check_library_events(ctx: RunContext[LibSyncDeps], search: str | None = None, days: int = 14) -> str:
    """List the library's upcoming events and programs from its LibCal
    calendar (read-only; patrons register on each event's own page).

    Args:
        search: Optional words to match, e.g. "storytime", "coding", "book club".
        days: How many days ahead to look (1 to 60, default 14).
    """
    config = ctx.deps.library_config
    try:
        secret = await get_library_secret(ctx.deps.http_client, config.id, "libcal_client_secret")
        events = await libcal.upcoming_events(ctx.deps.http_client, config.integration("libcal"), secret, search, days)
    except Exception as error:
        print("LibCal events lookup failed:", type(error).__name__)
        return "The events calendar is temporarily unavailable."
    if not events:
        matching = f' matching "{search}"' if search else ""
        return f"No upcoming events{matching} in the next {days} days."
    lines = ["Upcoming events:"]
    for event in events:
        details = "; ".join(filter(None, [event["location"], event["audience"] and f"for {event['audience']}"]))
        line = f"- {event['title']}, {event['start'] or 'date not listed'}"
        if details:
            line += f" ({details})"
        if event["url"]:
            line += f". Details and registration: {event['url']}"
        lines.append(line)
    return "\n".join(lines)

@chat_agent.tool(prepare=_when_signed_in_with_card)
async def check_my_account(ctx: RunContext[LibSyncDeps]) -> ToolReturn:
    """Look up the signed-in patron's own library account: how many items are
    checked out, overdue, or on hold, and any fees. Use only when the patron
    asks about their own account."""
    config, patron = ctx.deps.library_config, ctx.deps.patron
    try:
        password = await get_library_secret(ctx.deps.http_client, config.id, "sip2_password")
        async with SIP2Client(config.integration("sip2"), password) as sip:
            info = await sip.patron_information(patron.card)
    except Exception as error:
        print("Account lookup failed:", type(error).__name__)  # never log the card
        return ToolReturn(return_value="The library's account system didn't respond. Suggest asking library staff.")

    counts = info.counts
    # Privacy by design: the model (and so the AI provider) gets only counts.
    # The titles, which are library records protected by state law, go
    # straight to the patron's own screen in the account card's CUSTOM event.
    summary = (
        f"The patron has {counts.get('charged', 0)} item(s) checked out, {counts.get('overdue', 0)} overdue, "
        f"{counts.get('holds', 0)} hold(s), and fees of {info.fee_amount or '0.00'}. "
        "The titles are shown to the patron in an account card; don't ask them to repeat them, and don't guess them."
    )
    card = {
        "counts": counts,
        "items": info.items,
        "fees": info.fee_amount,
        "message": info.screen_message,
    }
    return ToolReturn(return_value=summary, metadata=_custom_event("account_summary", card))


@chat_agent.tool(prepare=_tool_group_switch("research"))
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


@chat_agent.tool(prepare=_tool_group_switch("citations"))
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
    message: str,
    http_client: httpx.AsyncClient,
    session_id: str,
    library_id: str | None = None,
    enabled_tools: frozenset[str] | None = None,
    library_config: LibraryConfig | None = None,
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
        deps = LibSyncDeps(
            http_client=http_client,
            library_id=library_id,
            enabled_tools=enabled_tools,
            library_config=library_config,
        )
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
    message: str,
    http_client: httpx.AsyncClient,
    session_id: str,
    library_id: str | None = None,
    enabled_tools: frozenset[str] | None = None,
    library_config: LibraryConfig | None = None,
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
    deps = LibSyncDeps(
            http_client=http_client,
            library_id=library_id,
            enabled_tools=enabled_tools,
            library_config=library_config,
        )
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
