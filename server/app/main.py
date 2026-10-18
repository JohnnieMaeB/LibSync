"""Main entry point for the FastAPI server.

Sets up the app, configures middleware (CORS, rate limiting), and registers
all API routes. Mirrors the structure of the original Express server.
"""

from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

import httpx
import logfire
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app import mcp_server
from app.config import LOGFIRE_INCLUDE_CONTENT, LOGFIRE_TOKEN, MCP_ENABLED
from app.rate_limit import limiter
from app.routers import (
    agent,
    chat,
    developer,
    documents,
    faq_sync,
    libraries,
    patron_history,
    patrons,
    pinecone_query,
    stats,
    widget,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # A single shared client (connection pooling) for tool calls to Open
    # Library, reused across every request for the life of the process.
    async with httpx.AsyncClient(timeout=10.0) as client, AsyncExitStack() as stack:
        app.state.http_client = client
        mcp_server.http_client = client
        if MCP_ENABLED:
            # A mounted app's own lifespan doesn't run, so the MCP server is
            # started here.
            await stack.enter_async_context(mcp_server.running())
        yield


app = FastAPI(title="LibSync Backend", lifespan=lifespan)

# Tracing is opt-in: only configured when a token is present (e.g. not set in
# CI/tests), so the free Logfire Hobby tier is never required to run the app.
if LOGFIRE_TOKEN:
    logfire.configure(token=LOGFIRE_TOKEN, service_name="libsync-backend")
    logfire.instrument_pydantic_ai(include_content=LOGFIRE_INCLUDE_CONTENT)
    logfire.instrument_fastapi(app)

# Rate limiting is enforced per-route via the @limiter.limit(...) decorator
# on the chat and query endpoints (see app/rate_limit.py); this just wires up
# the shared limiter instance and its 429 error response.
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"error": "Too many requests, please try again later."},
    )


# Enable Cross-Origin Resource Sharing (CORS) for all routes.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if MCP_ENABLED:
    app.mount("/mcp", mcp_server.asgi_app())
    app.add_middleware(mcp_server.ServeBarePath)

app.include_router(chat.router)
app.include_router(agent.router)
app.include_router(pinecone_query.router)
app.include_router(widget.router)
app.include_router(libraries.router)
app.include_router(documents.router)
app.include_router(stats.router)
app.include_router(faq_sync.router)
app.include_router(developer.router)
app.include_router(patrons.router)
app.include_router(patron_history.router)
