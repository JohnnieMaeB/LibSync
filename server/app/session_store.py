"""In-process conversation history store, keyed by client-minted session id.

Render's free instance has no durable disk and sleeps/restarts on idle, so
this deliberately trades persistence for staying at $0/month: history resets
on cold start rather than being backed by a paid database. Bounded by both
session count and per-session message count, with TTL eviction, so a single
long-lived process can't grow this dict unbounded.
"""

import time
from dataclasses import dataclass, field

from pydantic_ai.messages import ModelMessage

MAX_SESSIONS = 500
SESSION_TTL_SECONDS = 60 * 60
MAX_MESSAGES_PER_SESSION = 40


@dataclass
class _Session:
    messages: list[ModelMessage] = field(default_factory=list)
    last_used: float = field(default_factory=time.monotonic)


class SessionStore:
    def __init__(self, max_sessions: int = MAX_SESSIONS, ttl_seconds: float = SESSION_TTL_SECONDS):
        self._sessions: dict[str, _Session] = {}
        self._max_sessions = max_sessions
        self._ttl_seconds = ttl_seconds

    def get(self, session_id: str) -> list[ModelMessage]:
        self._evict_expired()
        session = self._sessions.get(session_id)
        if session is None:
            return []
        session.last_used = time.monotonic()
        return session.messages

    def append(self, session_id: str, new_messages: list[ModelMessage]) -> None:
        if not new_messages:
            return
        self._evict_expired()
        session = self._sessions.get(session_id)
        if session is None:
            self._evict_oldest_if_full()
            session = _Session()
            self._sessions[session_id] = session
        session.messages.extend(new_messages)
        session.messages = session.messages[-MAX_MESSAGES_PER_SESSION:]
        session.last_used = time.monotonic()

    def _evict_expired(self) -> None:
        now = time.monotonic()
        expired = [sid for sid, session in self._sessions.items() if now - session.last_used > self._ttl_seconds]
        for sid in expired:
            del self._sessions[sid]

    def _evict_oldest_if_full(self) -> None:
        if len(self._sessions) < self._max_sessions:
            return
        oldest_id = min(self._sessions, key=lambda sid: self._sessions[sid].last_used)
        del self._sessions[oldest_id]


session_store = SessionStore()
