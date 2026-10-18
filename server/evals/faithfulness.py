"""Policy-answer faithfulness, scored by Vectara's HHEM-2.1-Open
(NEXT_FEATURES.md P0.1, the offline half).

`app/grounding.py` catches wrong numbers deterministically. What it can't
catch is an invented detail with no number in it; production once added that
"the renewal option will be removed" for overdue items, which no policy says.
HHEM is a small open model (Apache 2.0, ~110M parameters) that scores how well
a premise (the policy text the agent retrieved) supports a hypothesis (the
answer), from 0 (unsupported) to 1 (supported).

It runs only in the weekly eval workflow, which installs torch and
transformers: it needs more memory than Render's free instance has, so it is
never in production. It is a **reported score, not a pass/fail gate**: HHEM
reaches about 67% balanced accuracy on adversarial FaithBench, so a low score
flags an answer for a person to read, not a failure.

Before scoring, the answer is cleaned (`clean_for_scoring`): markdown is
removed, and so are sentences that make no claim about the library: referrals
("ask library staff", which the system prompt requires), offers of help and
pleasantries. The policy text never contains them, so HHEM counts them as
unsupported. Trialing on the
real renewal policy, a correct answer ending in a referral scored 0.13; the
same answer without it scored 0.98, while an invented detail scored 0.01.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass

from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext

from evals.task import EvalInput, EvalOutput

HHEM_MODEL = "vectara/hallucination_evaluation_model"
# Pinned: loading it runs the model's own code (trust_remote_code), so take a
# known revision, not whatever the repo holds on the day.
HHEM_REVISION = "de9a5e6ba9ba49531a022dba17e35ffeb2a6fad8"
# Below this, the weekly summary lists the answer for a person to read.
REVIEW_BELOW = 0.5

# Sentences that make no claim about the library: referrals to staff (the
# system prompt asks for them), offers of help and pleasantries.
_NOT_A_CLAIM = re.compile(
    r"\b(library staff|staff member|librarian|front desk|circulation desk|ask (?:us|staff|a staff)|"
    r"contact (?:the library|us|staff)|reach out|call the library|visit the library|let me know|"
    r"feel free|happy (?:reading|to help)|hope (?:this|that) helps|any other questions|anything else)\b",
    re.IGNORECASE,
)
# Emoji and other pictographs (the model likes a closing 📚).
_PICTOGRAPHS = re.compile("[☀-➿🀀-🫿️‍]")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+|\n+")


def _strip_markdown(text: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # [label](url) -> label
    text = re.sub(r"^\s{0,3}(?:#{1,6}\s+|[-*+]\s+|\d+[.)]\s+|>\s?)", "", text, flags=re.MULTILINE)
    text = re.sub(r"(\*\*|__|\*|_|`)", "", text)
    return re.sub(r"^\s*\|?[-:| ]+\|?\s*$", "", text, flags=re.MULTILINE)  # table rules


def clean_for_scoring(reply: str, policy_text: str = "") -> str:
    """The answer's claims, as plain sentences: markdown removed, each line
    ending as a sentence, emoji removed, and sentences that make no claim
    (referrals, offers of help, pleasantries) dropped, unless the policy
    text itself uses the same words (the circulation desk can be a policy
    fact)."""
    sentences = []
    for chunk in _SENTENCE_END.split(_PICTOGRAPHS.sub("", _strip_markdown(reply))):
        sentence = chunk.strip()
        if not sentence:
            continue
        filler = _NOT_A_CLAIM.search(sentence)
        if filler and filler.group(0).casefold() not in policy_text.casefold():
            continue
        sentences.append(sentence if sentence[-1] in ".!?:" else sentence + ".")
    return " ".join(sentences)


Scorer = Callable[[list[tuple[str, str]]], list[float]]


def load_hhem() -> Scorer | None:
    """HHEM's scoring function, or None when torch/transformers aren't
    installed (everywhere but the weekly eval workflow)."""
    try:
        from transformers import AutoModelForSequenceClassification
    except ImportError:
        return None
    model = AutoModelForSequenceClassification.from_pretrained(
        HHEM_MODEL, trust_remote_code=True, revision=HHEM_REVISION
    )
    model.eval()
    return lambda pairs: [float(score) for score in model.predict(pairs)]


@dataclass
class PolicyFaithfulness(Evaluator[EvalInput, EvalOutput]):
    """HHEM score for answers that used the policy search; nothing for
    others. `scorer` is HHEM in the weekly run, or a stand-in in tests."""

    scorer: Scorer | None = None

    def evaluate(self, ctx: EvaluatorContext[EvalInput, EvalOutput]) -> dict[str, EvaluationReason]:
        if self.scorer is None or not ctx.output.policy_sources:
            return {}
        premise = "\n".join(ctx.output.policy_sources)
        hypothesis = clean_for_scoring(ctx.output.reply, premise)
        if not hypothesis:
            return {}
        score = self.scorer([(premise, hypothesis)])[0]
        return {"hhem": EvaluationReason(value=round(score, 3), reason=hypothesis)}
