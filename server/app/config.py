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
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PORT = int(os.getenv("PORT", "3000"))
IS_TEST_ENV = os.getenv("NODE_ENV") == "test" or os.getenv("ENV") == "test"
LOGFIRE_TOKEN = os.getenv("LOGFIRE_TOKEN")

# OpenAlex (Tier 2 research assistant) and Crossref (Tier 2 citation
# assistant) are free and keyless, but both ask callers to identify
# themselves via a contact email for their "polite pool" of higher, more
# reliable rate limits. OPENALEX_API_KEY is optional — OpenAlex's premium
# tier — and unused unless set.
OPENALEX_MAILTO = os.getenv("OPENALEX_MAILTO")
OPENALEX_API_KEY = os.getenv("OPENALEX_API_KEY")
CROSSREF_MAILTO = os.getenv("CROSSREF_MAILTO")
