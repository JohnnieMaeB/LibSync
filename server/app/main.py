"""Main entry point for the FastAPI server.

Sets up the app, configures middleware (CORS, rate limiting), and registers
all API routes. Mirrors the structure of the original Express server.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.rate_limit import limiter
from app.routers import chat, pinecone_query

app = FastAPI(title="LibSync Backend")

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

app.include_router(chat.router)
app.include_router(pinecone_query.router)
