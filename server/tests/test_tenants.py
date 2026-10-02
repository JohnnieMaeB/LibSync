import pytest

from pydantic_ai.models.test import TestModel

from app import tenants
from app.agent import chat_agent
from app.deps import LibSyncDeps


@pytest.fixture(autouse=True)
def fresh_namespace_cache():
    tenants.reset_namespace_cache()
    yield
    tenants.reset_namespace_cache()


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, None),
        ("", None),
        ("  Springfield-PL ", "springfield-pl"),
        ("lib_with_underscore", None),
        ("-leading-dash", None),
        ("a" * 64, None),
        ("ns1/../x", None),
    ],
)
def test_normalize_library_id(raw, expected):
    assert tenants.normalize_library_id(raw) == expected


def test_policy_namespace_falls_back_until_a_library_has_its_own(monkeypatch):
    monkeypatch.setattr(tenants, "list_namespaces", lambda: ["ns1", "springfield-pl"])
    assert tenants.policy_namespace("springfield-pl") == "springfield-pl"
    assert tenants.policy_namespace("shelbyville-pl") == "ns1"
    assert tenants.policy_namespace(None) == "ns1"


def test_namespace_list_is_cached_between_searches(monkeypatch):
    calls = {"n": 0}

    def counting_list():
        calls["n"] += 1
        return ["ns1"]

    monkeypatch.setattr(tenants, "list_namespaces", counting_list)
    for _ in range(3):
        tenants.policy_namespace("springfield-pl")
    assert calls["n"] == 1


@pytest.mark.parametrize(("library_id", "expected"), [("springfield-pl", "springfield-pl"), (None, "default")])
async def test_run_metadata_tags_the_library_for_usage_stats(library_id, expected):
    """Every agent run's Logfire span carries the library id (TIER8_PLAN.md §2.3)."""
    with chat_agent.override(model=TestModel(call_tools=[])):
        result = await chat_agent.run("hi", deps=LibSyncDeps(http_client=None, library_id=library_id))
    assert result.metadata == {"library_id": expected}
