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
