"""Environment configuration for the LibSync backend."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from server/.env into the process environment.
# This must happen before any client is initialized so tokens are available.
# The path is pinned relative to this file (not left to the default
# CWD-search behavior of a bare load_dotenv()) so it's found regardless of
# where the process is launched from.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Falls back to a placeholder so the providers can be constructed (e.g. for
# tests, or before a real token is configured); real chat calls will fail with
# an auth error until a valid token is set.
GROQ_API_KEY = os.getenv("GROQ_API_KEY") or "unset"
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN") or os.getenv("HF_TOKEN") or "unset"
# Optional extra fallback (NEXT_FEATURES.md P2.8): OpenRouter's free models,
# only when a key is set. See app/agent.py for the privacy routing it uses.
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY") or None
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PORT = int(os.getenv("PORT", "3000"))
IS_TEST_ENV = os.getenv("NODE_ENV") == "test" or os.getenv("ENV") == "test"
LOGFIRE_TOKEN = os.getenv("LOGFIRE_TOKEN")
# The MCP endpoint (app/mcp_server.py): on unless MCP_ENABLED=0.
MCP_ENABLED = os.getenv("MCP_ENABLED", "1").strip().lower() not in ("0", "false", "no")
MCP_RATE_LIMIT_PER_MINUTE = int(os.getenv("MCP_RATE_LIMIT_PER_MINUTE", "30"))
# Tier 8 (optional): per-library settings and the staff dashboard. Unset means
# every library uses the defaults and the embed snippet's attributes, as before.
SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").rstrip("/") or None
# Tier 8 (optional): a Logfire *read* token for per-library usage stats in the
# dashboard. Unset = the stats panel says it isn't set up.
LOGFIRE_READ_TOKEN = os.getenv("LOGFIRE_READ_TOKEN") or None
# Tier 9 (optional): signs and encrypts patron sessions. Unset = patron
# sign-in is off and the app stays fully anonymous, as before.
PATRON_SESSION_SECRET = os.getenv("PATRON_SESSION_SECRET") or None
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY") or None
# Patron messages and model replies stay out of traces unless explicitly
# turned on for debugging: library records are confidential by law in 48
# states + DC, and ALA's AI guidance asks vendors not to log reference
# interactions by default (TIER8_PLAN.md §2.8). Spans still record timing,
# tool names, token counts, errors and library_id.
LOGFIRE_INCLUDE_CONTENT = os.getenv("LOGFIRE_INCLUDE_CONTENT", "").lower() in ("1", "true", "yes")

# OpenAlex (Tier 2 research assistant) and Crossref (Tier 2 citation
# assistant) are free and keyless, but both ask callers to identify
# themselves via a contact email for their "polite pool" of higher, more
# reliable rate limits. OPENALEX_API_KEY is optional — OpenAlex's premium
# tier — and unused unless set.
OPENALEX_MAILTO = os.getenv("OPENALEX_MAILTO")
OPENALEX_API_KEY = os.getenv("OPENALEX_API_KEY")
CROSSREF_MAILTO = os.getenv("CROSSREF_MAILTO")
