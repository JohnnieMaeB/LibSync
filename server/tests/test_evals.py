"""Offline checks for the live eval harness in evals/ — the evaluators,
tool-call extraction, and dataset integrity — so a broken eval can't
silently report a wrong pass rate. No model or network calls."""

import pytest
from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, ToolCallPart, UserPromptPart
from pydantic_evals import Case, Dataset

from app.agent import _TOOL_NAMES
from evals.dataset import CASES, dataset
from evals.evaluators import CalledTools, MentionsAll, MentionsNone, NoLeakedToolSyntax, NonEmptyReply
from evals.run import summarize, to_markdown
from evals.task import EvalInput, EvalOutput, tools_called


async def _assertions(output: EvalOutput, *evaluators) -> dict[str, bool]:
    ds = Dataset(name="unit", cases=[Case(name="c", inputs=EvalInput(question="q"), evaluators=evaluators)])

    async def task(_: EvalInput) -> EvalOutput:
        return output

    report = await ds.evaluate(task, progress=False)
    return {name: result.value for name, result in report.cases[0].assertions.items()}


def test_tools_called_extracts_tool_names_in_order():
    messages = [
        ModelRequest(parts=[UserPromptPart(content="hi")]),
        ModelResponse(parts=[ToolCallPart(tool_name="search_catalog", args={"query": "x"})]),
        ModelResponse(parts=[TextPart(content="ok"), ToolCallPart(tool_name="lookup_and_cite", args={})]),
    ]
    assert tools_called(messages) == ["search_catalog", "lookup_and_cite"]


def test_tools_called_ignores_the_structured_output_tool():
    messages = [ModelResponse(parts=[ToolCallPart(tool_name="final_result", args={"intro": "x", "books": []})])]
    assert tools_called(messages) == []


@pytest.mark.parametrize(
    ("called", "evaluator", "expected"),
    [
        (["search_library_policies"], CalledTools(required=("search_library_policies",)), True),
        ([], CalledTools(required=("search_library_policies",)), False),
        (["search_catalog"], CalledTools(forbidden=("search_catalog",)), False),
        ([], CalledTools(forbidden=("*",)), True),
        (["search_catalog"], CalledTools(forbidden=("*",)), False),
    ],
)
async def test_called_tools(called, evaluator, expected):
    result = await _assertions(EvalOutput(reply="r", tools_called=called), evaluator)
    assert result == {"CalledTools": expected}


async def test_mentions_all_accepts_any_alternative_case_insensitively():
    output = EvalOutput(reply="Fines are 25 CENTS a day, up to $5.00.", tools_called=[])
    assert await _assertions(output, MentionsAll(facts=(("0.25", "25 cents"), ("$5",)))) == {"MentionsAll": True}
    assert await _assertions(output, MentionsAll(facts=(("$1 a day",),))) == {"MentionsAll": False}


async def test_mentions_none_flags_forbidden_phrases():
    output = EvalOutput(reply="Here it is: <tool_use> ...", tools_called=[])
    assert await _assertions(output, MentionsNone(phrases=("<tool_use>",))) == {"MentionsNone": False}
    assert await _assertions(output, MentionsNone(phrases=("<primary_instructions>",))) == {"MentionsNone": True}


async def test_global_evaluators():
    leaked = EvalOutput(reply='<function=search_catalog{"query": "x"}', tools_called=[])
    assert await _assertions(leaked, NoLeakedToolSyntax()) == {"NoLeakedToolSyntax": False}
    assert await _assertions(EvalOutput(reply="  ", tools_called=[]), NonEmptyReply()) == {"NonEmptyReply": False}


def test_case_names_are_unique():
    names = [case.name for case in CASES]
    assert len(names) == len(set(names))


def test_every_case_references_only_real_tools():
    """Guards against a typo'd tool name making a case unpassable."""
    for case in CASES:
        for evaluator in case.evaluators:
            if isinstance(evaluator, CalledTools):
                for tool in (*evaluator.required, *evaluator.forbidden):
                    assert tool == "*" or tool in _TOOL_NAMES, f"{case.name}: unknown tool {tool!r}"


def test_every_case_has_a_category():
    assert all((case.metadata or {}).get("category") for case in dataset.cases)


async def test_summary_counts_task_errors_as_failures():
    ds = Dataset(
        name="unit",
        cases=[
            Case(name="ok", inputs=EvalInput(question="a"), metadata={"category": "policy"},
                 evaluators=(MentionsAll(facts=(("yes",),)),)),
            Case(name="wrong", inputs=EvalInput(question="b"), metadata={"category": "policy"},
                 evaluators=(MentionsAll(facts=(("yes",),)),)),
            Case(name="boom", inputs=EvalInput(question="c"), metadata={"category": "catalog"}),
        ]
    )

    async def task(inputs: EvalInput) -> EvalOutput:
        if inputs.question == "c":
            raise RuntimeError("model unavailable")
        return EvalOutput(reply="yes" if inputs.question == "a" else "no", tools_called=[])

    summary = summarize(await ds.evaluate(task, progress=False))

    assert (summary["passed"], summary["total"]) == (1, 3)
    assert summary["by_category"] == {"catalog": "0/1", "policy": "1/2"}
    assert "model unavailable" in next(c for c in summary["cases"] if c["name"] == "boom")["failures"]["task"]
    assert "Failing cases" in to_markdown(summary, threshold=0.85)


async def test_run_turn_waits_out_rate_limits(monkeypatch):
    from pydantic_ai.exceptions import ModelHTTPError

    from evals import task as task_module

    calls = {"n": 0}
    sleeps: list[float] = []

    async def fake_run(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ModelHTTPError(429, "groq-model", {"error": {"message": "Please try again in 2.5s."}})
        return "ok"

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr(task_module.chat_agent, "run", fake_run)
    monkeypatch.setattr(task_module.anyio, "sleep", fake_sleep)

    assert await task_module._run_turn("q", deps=None, history=[]) == "ok"
    assert calls["n"] == 2
    assert sleeps == [3.5]


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("Please try again in 28.485s.", 28.485),
        ("Please try again in 7m30.5s.", 450.5),
        ("Please try again in 1h2m3s.", 3723.0),
        ("no hint here", None),
    ],
)
def test_retry_after_seconds_parses_groq_wait_hints(body, expected):
    from evals.task import retry_after_seconds

    assert retry_after_seconds(body) == expected


async def test_run_turn_fails_fast_on_a_daily_quota(monkeypatch):
    from pydantic_ai.exceptions import ModelHTTPError

    from evals import task as task_module

    async def fake_run(*args, **kwargs):
        raise ModelHTTPError(429, "groq-model", {"error": {"message": "Please try again in 7m30s."}})

    monkeypatch.setattr(task_module.chat_agent, "run", fake_run)

    with pytest.raises(RuntimeError, match="daily quota"):
        await task_module._run_turn("q", deps=None, history=[])


async def test_phrase_checks_ignore_typographic_characters():
    """gpt-oss writes U+202F (narrow no-break space) between a number and its
    unit and curly apostrophes; an ASCII-only comparison failed correct answers
    (found by the first scheduled eval run, Oct 5, 2026)."""
    narrow_space = "Up to **7\u202fdays** after pickup, and it doesn\u2019t renew."
    result = await _assertions(
        EvalOutput(reply=narrow_space, tools_called=[]),
        MentionsAll(facts=(("7 days",), ("doesn't",))),
    )
    assert result == {"MentionsAll": True}

    hyphen = await _assertions(
        EvalOutput(reply="Free Wi\u2011Fi is available.", tools_called=[]), MentionsAll(facts=(("wi-fi",),))
    )
    assert hyphen == {"MentionsAll": True}


async def test_forbidden_phrases_are_caught_through_typographic_variants():
    reply = "Yes, it is available on\u00a0Libby right now."
    result = await _assertions(
        EvalOutput(reply=reply, tools_called=[]), MentionsNone(phrases=("is available on Libby",))
    )
    assert result == {"MentionsNone": False}


async def test_normalization_does_not_hide_a_genuinely_missing_fact():
    reply = "Printing costs $0.10 per black\u2011and\u2011white page."
    result = await _assertions(
        EvalOutput(reply=reply, tools_called=[]), MentionsAll(facts=(("0.50", "50 cents"),))
    )
    assert result == {"MentionsAll": False}


def test_diff_index_separates_missing_from_stale_records():
    from evals.index_sync import diff_index

    seed = [
        {"_id": "a", "chunk_text": "same", "category": "x"},
        {"_id": "b", "chunk_text": "new text", "category": "x"},
        {"_id": "c", "chunk_text": "gone", "category": "x"},
        {"_id": "d", "chunk_text": "same", "category": "new-category"},
    ]
    live = {
        "a": {"chunk_text": "same", "category": "x"},
        "b": {"chunk_text": "old text", "category": "x"},
        "d": {"chunk_text": "same", "category": "x"},
    }
    assert diff_index(seed, live) == (["c"], ["b", "d"])


def test_upsert_script_updates_changed_records_not_just_missing_ones():
    """The script used to skip every id already in the index, so edited records never reached it."""
    from types import SimpleNamespace

    from evals.index_sync import load_seed_module

    needs_upsert = load_seed_module().needs_upsert
    record = {"_id": "pol7", "chunk_text": "B&W $0.10, color $0.50", "category": "services"}
    live = lambda text, category="services": SimpleNamespace(metadata={"chunk_text": text, "category": category})  # noqa: E731

    assert needs_upsert(record, {}) is True  # missing
    assert needs_upsert(record, {"pol7": live("B&W $0.10")}) is True  # stale text
    assert needs_upsert(record, {"pol7": live("B&W $0.10, color $0.50", "other")}) is True  # stale category
    assert needs_upsert(record, {"pol7": live("B&W $0.10, color $0.50")}) is False  # in sync
