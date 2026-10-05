"""Rule-based evaluators for the LibSync agent evals.

Deliberately deterministic (no LLM-as-judge): every check here is a plain
string or tool-name comparison, so a failing case points at a concrete,
reproducible reason, and running the suite costs no model calls beyond the
agent's own. Phrase checks are case-insensitive substring matches on
*normalized* text (see `normalize`): models write typographic characters
(curly apostrophes, narrow no-break spaces between a number and its unit,
non-breaking hyphens), and an ASCII-only comparison scored correct answers
as failures.
"""

import re
import unicodedata
from dataclasses import dataclass, field

from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext

from app.agent import _LEAKED_TOOL_CALL_PATTERN
from evals.task import EvalInput, EvalOutput


_TYPOGRAPHIC_TO_ASCII = {
    0x2018: "'",  # left single quotation mark
    0x2019: "'",  # right single quotation mark / curly apostrophe
    0x201C: '"',
    0x201D: '"',
    0x2010: "-",  # hyphen
    0x2011: "-",  # non-breaking hyphen
    0x2012: "-",
    0x2013: "-",  # en dash
    0x2014: "-",  # em dash
}


def normalize(text: str) -> str:
    """Folds the typographic variants models emit into plain ASCII forms so
    phrase checks compare meaning, not character encoding: NFKC (which turns
    no-break and narrow no-break spaces into spaces), curly quotes and
    non-breaking hyphens to ASCII, whitespace collapsed, case folded."""
    text = unicodedata.normalize("NFKC", text).translate(_TYPOGRAPHIC_TO_ASCII)
    return re.sub(r"\s+", " ", text).casefold()


def _contains(text: str, phrase: str) -> bool:
    return normalize(phrase) in normalize(text)


@dataclass
class CalledTools(Evaluator[EvalInput, EvalOutput]):
    """Every tool in `required` was called during the final turn, and none in
    `forbidden` was. `forbidden=("*",)` means no tool call at all."""

    required: tuple[str, ...] = ()
    forbidden: tuple[str, ...] = ()

    def evaluate(self, ctx: EvaluatorContext[EvalInput, EvalOutput]) -> EvaluationReason:
        called = set(ctx.output.tools_called)
        missing = [tool for tool in self.required if tool not in called]
        if "*" in self.forbidden:
            unexpected = sorted(called)
        else:
            unexpected = [tool for tool in self.forbidden if tool in called]
        if missing or unexpected:
            parts = []
            if missing:
                parts.append(f"missing {missing}")
            if unexpected:
                parts.append(f"unexpected {unexpected}")
            return EvaluationReason(value=False, reason=f"{'; '.join(parts)} (called {sorted(called)})")
        return EvaluationReason(value=True)


@dataclass
class MentionsAll(Evaluator[EvalInput, EvalOutput]):
    """Each entry must appear in the reply. An entry is a tuple of
    acceptable alternatives, e.g. `("three weeks", "3 weeks", "21 days")`."""

    facts: tuple[tuple[str, ...], ...] = ()

    def evaluate(self, ctx: EvaluatorContext[EvalInput, EvalOutput]) -> EvaluationReason:
        missing = [alts for alts in self.facts if not any(_contains(ctx.output.reply, alt) for alt in alts)]
        if missing:
            return EvaluationReason(value=False, reason=f"reply is missing {[' | '.join(alts) for alts in missing]}")
        return EvaluationReason(value=True)


@dataclass
class MentionsNone(Evaluator[EvalInput, EvalOutput]):
    """None of these phrases may appear in the reply — fabrication and
    prompt-leak guards."""

    phrases: tuple[str, ...] = ()

    def evaluate(self, ctx: EvaluatorContext[EvalInput, EvalOutput]) -> EvaluationReason:
        found = [phrase for phrase in self.phrases if _contains(ctx.output.reply, phrase)]
        if found:
            return EvaluationReason(value=False, reason=f"reply contains forbidden {found}")
        return EvaluationReason(value=True)


@dataclass
class NoLeakedToolSyntax(Evaluator[EvalInput, EvalOutput]):
    """The reply never contains raw tool-call syntax — the same pattern the
    agent's own output validator retries on, checked end to end here."""

    def evaluate(self, ctx: EvaluatorContext[EvalInput, EvalOutput]) -> bool:
        return not _LEAKED_TOOL_CALL_PATTERN.search(ctx.output.reply)


@dataclass
class NonEmptyReply(Evaluator[EvalInput, EvalOutput]):
    min_chars: int = field(default=1)

    def evaluate(self, ctx: EvaluatorContext[EvalInput, EvalOutput]) -> bool:
        return len(ctx.output.reply.strip()) >= self.min_chars
