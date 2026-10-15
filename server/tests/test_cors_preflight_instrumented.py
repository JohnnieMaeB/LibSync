"""Regression test for a bug that curl and the rest of the suite can't see.

With LOGFIRE_TOKEN set, app/main.py calls logfire.instrument_fastapi(app). For a
while, FastAPI 0.137+ combined with the OpenTelemetry FastAPI instrumentation that
Logfire resolved to (0.63b1) made every CORS preflight (an OPTIONS request) return
500: the instrumentation read .path off routes registered through
include_router(), and FastAPI's new _IncludedRouter type has none. The deployed
frontend and API are on different origins, so every real browser request starts
with a preflight. curl never sends one, so the API looked healthy.

The test builds a fresh app (the real routers, real CORS middleware), instruments
it exactly as main.py does, and asserts a preflight still succeeds. It stays in
the suite so the dependency pin that used to guard this can't quietly come back
as a different failure.
"""

import logfire
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from app.routers import agent, chat


def test_instrumented_app_answers_cors_preflight():
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://example.github.io"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(chat.router)
    app.include_router(agent.router)

    logfire.configure(send_to_logfire=False, console=False)
    logfire.instrument_fastapi(app)

    response = TestClient(app, raise_server_exceptions=False).options(
        "/agent",
        headers={
            "Origin": "https://example.github.io",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://example.github.io"
