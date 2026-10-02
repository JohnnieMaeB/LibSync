"""The eval task: run one (possibly multi-turn) conversation through the real
agent and capture the final reply plus which tools the final turn called."""

import re
from collections.abc import Sequence

import anyio
import httpx
from pydantic import BaseModel, Field
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart

from app.agent import chat_agent
from app.deps import LibSyncDeps
from app.schemas import BookResult


class EvalInput(BaseModel):
    question: str
    # Earlier user turns, run first (in order) on the same message history —
    # how the continuity cases prove context carries across turns.
    history: list[str] = Field(default_factory=list)


class EvalOutput(BaseModel):
    reply: str
    tools_called: list[str]


# pydantic-ai delivers structured output (a `BookResult`) through its own
# output tool; that's how the reply is returned, not a tool the agent chose.
_OUTPUT_TOOL_PREFIX = "final_result"


def tools_called(messages: Sequence[ModelMessage]) -> list[str]:
    """Tool names the model called, in order, across `messages` — excluding
    pydantic-ai's output tool."""
    return [
        part.tool_name
        for message in messages
        if isinstance(message, ModelResponse)
        for part in message.parts
        if isinstance(part, ToolCallPart) and not part.tool_name.startswith(_OUTPUT_TOOL_PREFIX)
    ]


def reply_text(output: str | BookResult) -> str:
    """Flatten a structured `BookResult` into text so phrase checks work on
    either output type."""
    if isinstance(output, BookResult):
        return output.model_dump_json()
    return output


# Groq phrases the wait as "28.4s", "7m30.5s", or "1h2m3s" depending on
# which limit (per-minute vs. per-day) was hit.
_RETRY_AFTER_PATTERN = re.compile(r"try again in (?:(\d+)h)?(?:(\d+)m)?([\d.]+)s")
_MAX_RATE_LIMIT_RETRIES = 3
# Waits longer than this mean a daily quota, not a per-minute one — it won't
# clear within a run, so fail the case now instead of stalling the suite.
_MAX_RETRY_WAIT_SECONDS = 90
CASE_TIMEOUT_SECONDS = 180


def retry_after_seconds(body: object) -> float | None:
    match = _RETRY_AFTER_PATTERN.search(str(body))
    if not match:
        return None
    hours, minutes, seconds = match.groups()
    return int(hours or 0) * 3600 + int(minutes or 0) * 60 + float(seconds)


async def _run_turn(question: str, deps: LibSyncDeps, history: list[ModelMessage]):
    """One agent turn, waiting out free-tier 429s instead of scoring them as
    failures — a rate limit says nothing about the agent's behavior. Groq's
    429 body says how long to wait ("Please try again in 28.4s")."""
    for attempt in range(_MAX_RATE_LIMIT_RETRIES + 1):
        try:
            return await chat_agent.run(question, deps=deps, message_history=history)
        except ModelHTTPError as error:
            if error.status_code != 429 or attempt == _MAX_RATE_LIMIT_RETRIES:
                raise
            retry_after = retry_after_seconds(error.body)
            if retry_after is not None and retry_after > _MAX_RETRY_WAIT_SECONDS:
                raise RuntimeError(f"Rate limit won't clear for {retry_after:.0f}s (daily quota?): {error.body}") from error
            wait = retry_after + 1 if retry_after is not None else 30
            print(f"  rate-limited, waiting {wait:.0f}s ({question[:50]!r})", flush=True)
            await anyio.sleep(wait)


def make_task(http_client: httpx.AsyncClient, pace_seconds: float = 0.0):
    """Builds the task callable for `Dataset.evaluate`. `pace_seconds` sleeps
    before each turn to stay under Groq's free-tier rate limits."""

    async def run_conversation(inputs: EvalInput) -> EvalOutput:
        deps = LibSyncDeps(http_client=http_client)
        history: list[ModelMessage] = []
        try:
            # One hung request (no provider-side timeout) must fail its own
            # case, not stall the whole suite into the workflow's time limit.
            with anyio.fail_after(CASE_TIMEOUT_SECONDS):
                for turn in inputs.history:
                    await anyio.sleep(pace_seconds)
                    result = await _run_turn(turn, deps, history)
                    history = result.all_messages()

                await anyio.sleep(pace_seconds)
                result = await _run_turn(inputs.question, deps, history)
        except Exception as error:
            print(f"  FAILED: {inputs.question[:60]!r} -> {type(error).__name__}: {str(error)[:200]}", flush=True)
            raise
        output = EvalOutput(reply=reply_text(result.output), tools_called=tools_called(result.new_messages()))
        # The rich progress bar doesn't render in CI logs; this does.
        print(f"  done: {inputs.question[:60]!r} -> tools {output.tools_called}", flush=True)
        return output

    return run_conversation
