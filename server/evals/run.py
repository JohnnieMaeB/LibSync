"""Run the live agent evals and gate on the case pass rate.

    uv run python -m evals.run                    # full suite
    uv run python -m evals.run --case late-fees   # one case (repeatable)
    uv run python -m evals.run --threshold 0.9
    uv run python -m evals.run --model groq:openai/gpt-oss-120b   # try another model
    uv run python -m evals.run --with-fallback   # the full FallbackModel chain, as production runs it

Needs real GROQ_API_KEY and PINECONE_API_KEY (server/.env or the
environment). Writes evals/results.json, and a markdown summary to
$GITHUB_STEP_SUMMARY when running in Actions. Exits 1 if the share of
passing cases falls below --threshold.
"""

import argparse
import asyncio
import json
import os
import sys
from collections import defaultdict
from contextlib import nullcontext
from pathlib import Path

import httpx
from pydantic_evals import Dataset

from app.agent import _groq_model, chat_agent
from app.config import GROQ_API_KEY, PINECONE_API_KEY
from evals.dataset import dataset
from evals.task import make_task

RESULTS_PATH = Path(__file__).parent / "results.json"


def summarize(report) -> dict:
    """Per-case pass/fail (a case passes only if every assertion passed and
    the task didn't raise), with failure reasons, plus per-category rates."""
    cases = []
    for case in report.cases:
        failed = {
            name: (result.reason or "failed")
            for name, result in case.assertions.items()
            if not result.value
        }
        cases.append({
            "name": case.name,
            "category": (case.metadata or {}).get("category", "other"),
            "passed": not failed,
            "failures": failed,
            "tools_called": case.output.tools_called,
            "duration_s": round(case.task_duration, 2),
            # Kept for failing cases only: a phrase check that missed needs
            # the actual reply to tell a real omission from a wording the
            # check didn't anticipate.
            **({"reply": case.output.reply[:600]} if failed else {}),
        })
    for failure in report.failures:
        cases.append({
            "name": failure.name,
            "category": (failure.metadata or {}).get("category", "other"),
            "passed": False,
            "failures": {"task": failure.error_message},
            "tools_called": [],
            "duration_s": None,
        })

    by_category: dict[str, list[bool]] = defaultdict(list)
    for case in cases:
        by_category[case["category"]].append(case["passed"])

    passed = sum(case["passed"] for case in cases)
    return {
        "passed": passed,
        "total": len(cases),
        "pass_rate": passed / len(cases) if cases else 0.0,
        "by_category": {cat: f"{sum(r)}/{len(r)}" for cat, r in sorted(by_category.items())},
        "cases": sorted(cases, key=lambda c: (c["passed"], c["name"])),
    }


def to_markdown(summary: dict, threshold: float) -> str:
    status = "✅" if summary["pass_rate"] >= threshold else "❌"
    lines = [
        f"## {status} LibSync agent evals: {summary['passed']}/{summary['total']} "
        f"({summary['pass_rate']:.0%}, threshold {threshold:.0%})",
        "",
        "| Category | Passed |",
        "|---|---|",
        *(f"| {cat} | {rate} |" for cat, rate in summary["by_category"].items()),
    ]
    failing = [c for c in summary["cases"] if not c["passed"]]
    if failing:
        lines += ["", "### Failing cases", "", "| Case | Why | Tools called |", "|---|---|---|"]
        for case in failing:
            why = "; ".join(f"{k}: {v}" for k, v in case["failures"].items()).replace("|", "\\|")
            lines.append(f"| `{case['name']}` | {why} | {', '.join(case['tools_called']) or '—'} |")
    return "\n".join(lines) + "\n"


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--case", action="append", help="Run only the named case(s).")
    parser.add_argument("--threshold", type=float, default=0.85, help="Minimum case pass rate (default 0.85).")
    parser.add_argument("--concurrency", type=int, default=1, help="Cases run at once (default 1, for Groq's free tier).")
    parser.add_argument(
        "--model",
        help="Override the agent's model with a pydantic-ai model string (e.g. groq:qwen/qwen3.8-27b) — "
        "for vetting a replacement before changing app/agent.py.",
    )
    parser.add_argument(
        "--with-fallback",
        action="store_true",
        help="Run the full FallbackModel chain instead of the primary model alone. Off by default: every "
        "rate-limited eval turn would otherwise spill onto the Hugging Face fallback, whose free credit "
        "(~$0.10/month) a single suite run can exhaust, leaving production with no fallback.",
    )
    parser.add_argument("--pace", type=float, default=3.0, help="Seconds to wait before each agent turn (default 3).")
    args = parser.parse_args()

    if GROQ_API_KEY == "unset" or not PINECONE_API_KEY:
        print("GROQ_API_KEY and PINECONE_API_KEY must be set to run live evals.", file=sys.stderr)
        return 2

    selected = dataset
    if args.case:
        unknown = set(args.case) - {case.name for case in dataset.cases}
        if unknown:
            print(f"Unknown case(s): {sorted(unknown)}", file=sys.stderr)
            return 2
        selected = Dataset(
            name=dataset.name,
            cases=[case for case in dataset.cases if case.name in args.case],
            evaluators=dataset.evaluators,
        )

    if args.model:
        model_override = chat_agent.override(model=args.model)
    elif args.with_fallback:
        model_override = nullcontext()
    else:
        model_override = chat_agent.override(model=_groq_model)
    async with httpx.AsyncClient(timeout=30) as http_client:
        with model_override:
            report = await selected.evaluate(
                make_task(http_client, pace_seconds=args.pace),
                name=args.model or ("libsync-agent (with fallback)" if args.with_fallback else _groq_model.model_name),
                max_concurrency=args.concurrency,
            )

    report.print(include_input=False, include_output=False, include_durations=True, include_reasons=True)
    summary = summarize(report)
    RESULTS_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    markdown = to_markdown(summary, args.threshold)
    print(markdown)
    if step_summary := os.getenv("GITHUB_STEP_SUMMARY"):
        with open(step_summary, "a", encoding="utf-8") as f:
            f.write(markdown)

    return 0 if summary["pass_rate"] >= args.threshold else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
