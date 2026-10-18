"""LibSync as an MCP server (NEXT_FEATURES.md P2.7).

Library staff increasingly work in their own AI tools (Claude, ChatGPT,
Copilot). This exposes LibSync's grounded lookups to them as Model Context
Protocol tools over Streamable HTTP at /mcp: policy search, catalog search,
read-alikes, scholarly search and citations. Each tool is the same service
code the patron assistant uses, called directly: no model runs here, so no
Groq quota is spent and nothing can be embellished.

Which library: an `X-LibSync-Key` header (a key from the dashboard's
Developer panel) selects that library's policies, catalog and tool switches;
without one, the tools use the shared demo policies and Open Library. Either
way the data is what a patron could already see.

Abuse protection: a per-IP limit (MCP_RATE_LIMIT_PER_MINUTE), and
MCP_ENABLED=0 turns the endpoint off.
"""

import time
from collections import defaultdict, deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Literal

import anyio
import httpx
from mcp.server.mcpserver import Context, MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from app.api_keys import library_for_key
from app.config import MCP_RATE_LIMIT_PER_MINUTE
from app.library_config import LibraryConfig, get_library_config
from app.services import catalog, citation_service, crossref_service, openalex_service, readers_advisory
from app.services.pinecone_service import search_pinecone
from app.tenants import TOOL_GROUPS, policy_namespace

RATE_LIMIT_PER_MINUTE = MCP_RATE_LIMIT_PER_MINUTE

server = MCPServer(
    name="libsync",
    title="LibSync",
    instructions=(
        "Grounded lookups for public and academic libraries: this library's policies, its catalog, "
        "read-alike recommendations, scholarly papers (OpenAlex) and citations (Crossref). Answer only from "
        "what the tools return, and say which source each fact came from."
    ),
    website_url="https://github.com/JohnnieMaeB/LibSync",
    log_level="WARNING",
)

# Set by the FastAPI lifespan (app/main.py): the app's shared HTTP client.
http_client: httpx.AsyncClient | None = None


def _client() -> httpx.AsyncClient:
    if http_client is None:  # pragma: no cover - the lifespan always sets it
        raise RuntimeError("LibSync MCP server used outside the app")
    return http_client


async def _library(ctx: Context) -> LibraryConfig | None:
    """The library named by the caller's API key, if any. A missing or
    unknown key means the demo library, never an error: the demo data is
    public anyway."""
    key = (ctx.headers or {}).get("x-libsync-key")
    if not key:
        return None
    library_id = await library_for_key(_client(), key)
    return await get_library_config(_client(), library_id) if library_id else None


def _allowed(config: LibraryConfig | None, group: str) -> bool:
    """A library's dashboard switches apply here too, including turning its
    AI assistant off (MCP clients are AI tools)."""
    if config is None:
        return True
    return config.ai_enabled and (config.enabled_tools is None or group in config.enabled_tools)


def _switched_off(group: str) -> dict:
    return {"error": f"This library has switched off {group} ({TOOL_GROUPS[group]}) or its AI assistant."}


@server.tool()
async def search_library_policies(question: str, ctx: Context) -> dict[str, Any]:
    """Search the library's own policies (fines, loans, renewals, cards, rooms,
    computers, accessibility...) and return the matching policy text verbatim."""
    config = await _library(ctx)
    if not _allowed(config, "policies"):
        return _switched_off("policies")
    results = await anyio.to_thread.run_sync(
        lambda: search_pinecone(question, 3, namespace=policy_namespace(config.id if config else None))
    )
    matches = [m for m in results.get("matches", []) if m.get("text")]
    return {
        "source": f"{config.name} policies" if config else "LibSync demo library policies",
        "policies": [{"text": m["text"], "category": m.get("category")} for m in matches],
    }


@server.tool()
async def search_catalog(query: str, ctx: Context) -> dict[str, Any]:
    """Search the library's catalog (or Open Library when none is connected)
    for a title or author, with availability."""
    config = await _library(ctx)
    if not _allowed(config, "catalog"):
        return _switched_off("catalog")
    search = await catalog.search_catalog(_client(), config, query, limit=5)
    return {"source": search.source, "fell_back": search.fell_back, "books": search.results}


@server.tool()
async def recommend_books(
    ctx: Context,
    like: str | None = None,
    about: str | None = None,
    audience: Literal["children", "teen", "adult"] | None = None,
) -> dict[str, Any]:
    """Read-alikes for a book (`like`) or books on a topic (`about`), chosen
    from Open Library subjects and, when the library's catalog is connected,
    only from titles it holds."""
    config = await _library(ctx)
    if not _allowed(config, "recommendations"):
        return _switched_off("recommendations")
    if not like and not about:
        return {"error": "Give a book you enjoyed (like) or a topic (about)."}
    books, source, subjects = await readers_advisory.recommend(_client(), config, like=like, about=about, audience=audience)
    return {"source": source, "subjects": subjects, "books": books}


@server.tool()
async def search_scholarly_works(query: str, ctx: Context) -> dict[str, Any]:
    """Search OpenAlex, an open index of scholarly papers, with citation
    counts and open-access status."""
    config = await _library(ctx)
    if not _allowed(config, "research"):
        return _switched_off("research")
    works = await openalex_service.search_scholarly_works(_client(), query, limit=5)
    return {"source": "OpenAlex", "works": works}


@server.tool()
async def cite(
    ctx: Context, style: Literal["apa", "mla", "chicago"] = "apa", doi: str | None = None, title: str | None = None
) -> dict[str, Any]:
    """Format a citation from the work's real Crossref record (by DOI, or by
    title and author) using the official CSL style."""
    config = await _library(ctx)
    if not _allowed(config, "citations"):
        return _switched_off("citations")
    if not doi and not title:
        return {"error": "Give a DOI or a title."}
    work = await crossref_service.lookup_work(_client(), doi=doi, title=title)
    if work is None:
        return {"error": "No matching work was found on Crossref."}
    return {"source": "Crossref", "style": style, "doi": work.get("DOI"), "citation": citation_service.format_citation(work, style)}


class RateLimit:
    """Per-IP requests per minute for the MCP endpoint (slowapi's decorators
    only cover FastAPI routes, and this is a mounted ASGI app)."""

    def __init__(self, app, per_minute: int = RATE_LIMIT_PER_MINUTE):
        self.app = app
        self.per_minute = per_minute
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope.get("method") == "POST":
            ip = (scope.get("client") or ("unknown",))[0]
            forwarded = dict(scope.get("headers") or []).get(b"x-forwarded-for")
            if forwarded:  # Render's proxy: the first address is the caller
                ip = forwarded.decode().split(",")[0].strip()
            now = time.monotonic()
            window = self.hits[ip]
            while window and now - window[0] > 60:
                window.popleft()
            if len(window) >= self.per_minute:
                await send({"type": "http.response.start", "status": 429, "headers": [(b"content-type", b"application/json")]})
                await send({"type": "http.response.body", "body": b'{"error": "Too many requests, please try again later."}'})
                return
            window.append(now)
        await self.app(scope, receive, send)


# The MCP app for the current app lifespan. The SDK's session manager runs
# once per instance, so each startup builds a fresh one (`running`), and the
# mounted app delegates to it.
_current = None


@asynccontextmanager
async def running() -> AsyncIterator[None]:
    """Serve /mcp for the life of the FastAPI app: stateless JSON-over-HTTP (no
    sessions to keep on a single small instance). Host checks are off because
    it serves a public hostname behind Render's proxy; there is nothing
    private to rebind to."""
    global _current
    app = server.streamable_http_app(
        streamable_http_path="/",
        json_response=True,
        stateless_http=True,
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )
    async with server.session_manager.run():
        _current = app
        try:
            yield
        finally:
            _current = None


async def _delegate(scope, receive, send):
    if _current is None:
        await send({"type": "http.response.start", "status": 503, "headers": [(b"content-type", b"application/json")]})
        await send({"type": "http.response.body", "body": b'{"error": "The MCP endpoint is starting."}'})
        return
    await _current(scope, receive, send)


def asgi_app():
    """What app/main.py mounts at /mcp."""
    return RateLimit(_delegate)
