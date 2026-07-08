"""Environment configuration for the LibSync backend."""

import os

from dotenv import load_dotenv

# Load environment variables from a .env file into the process environment.
# This must happen before any client is initialized so tokens are available.
load_dotenv()

# Falls back to a placeholder so the HuggingFace provider can be constructed
# (e.g. for tests, or before a real token is configured); real chat calls will
# fail with an auth error until a valid token is set.
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN") or os.getenv("HF_TOKEN") or "unset"
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PORT = int(os.getenv("PORT", "3000"))
IS_TEST_ENV = os.getenv("NODE_ENV") == "test" or os.getenv("ENV") == "test"
