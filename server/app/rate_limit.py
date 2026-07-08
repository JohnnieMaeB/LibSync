"""Shared rate limiter, matching the original express-rate-limit configuration
(100 requests per 15 minutes per client IP)."""

from slowapi import Limiter
from slowapi.util import get_remote_address

RATE_LIMIT = "100/15 minutes"

limiter = Limiter(key_func=get_remote_address)
