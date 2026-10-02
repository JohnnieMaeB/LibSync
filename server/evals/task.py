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


def tools_called(messages: Sequence[ModelMessage]) -> list[str]:
    """Tool names the model called, in order, across `messages`."""
    return [
        part.tool_name
        for message in messages
        if isinstance(message, ModelResponse)
        for part in message.parts
        if isinstance(part, ToolCallPart)
    ]


def reply_text(output: str | BookResult) -> str:
    """Flatten a structured `BookResult` into text so phrase checks work on
    either output type."""
    if isinstance(output, BookResult):
        return output.model_dump_json()
    return output


_RETRY_AFTER_PATTERN = re.compile(r"try again in ([\d.]+)s")
_MAX_RATE_LIMIT_RETRIES = 3


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
            match = _RETRY_AFTER_PATTERN.search(str(error.body))
            wait = float(match.group(1)) + 1 if match else 30
            print(f"  rate-limited, waiting {wait:.0f}s ({question[:50]!r})", flush=True)
            await anyio.sleep(wait)


def make_task(http_client: httpx.AsyncClient, pace_seconds: float = 0.0):
    """Builds the task callable for `Dataset.evaluate`. `pace_seconds` sleeps
    before each turn to stay under Groq's free-tier rate limits."""

    async def run_conversation(inputs: EvalInput) -> EvalOutput:
        deps = LibSyncDeps(http_client=http_client)
        history: list[ModelMessage] = []
        for turn in inputs.history:
            await anyio.sleep(pace_seconds)
            result = await _run_turn(turn, deps, history)
            history = result.all_messages()

        await anyio.sleep(pace_seconds)
        result = await _run_turn(inputs.question, deps, history)
        output = EvalOutput(reply=reply_text(result.output), tools_called=tools_called(result.new_messages()))
        # The rich progress bar doesn't render in CI logs; this does.
        print(f"  done: {inputs.question[:60]!r} -> tools {output.tools_called}", flush=True)
        return output

    return run_conversation
