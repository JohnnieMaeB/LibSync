"""Unit tests for the Tier 6 embeddable-widget allowlist (app/widget_registry.py) —
pure logic, no HTTP layer, no live calls. Route-level wiring (grace
enforcement on /agent and /chat, the /widget/register endpoint) is covered
in test_agent_endpoint.py, test_chat.py, and test_widget_endpoint.py."""

import pytest

from app.widget_registry import WidgetRegistry, check_widget_registration


@pytest.fixture()
def registry():
    return WidgetRegistry(grace_limit=3)


class TestRegister:
    def test_first_registration_claims_the_library_id(self, registry):
        assert registry.register("acme-library", "https://acme.example") is True
        assert registry.is_registered("acme-library", "https://acme.example") is True

    def test_re_registering_the_same_origin_is_a_no_op_success(self, registry):
        registry.register("acme-library", "https://acme.example")
        assert registry.register("acme-library", "https://acme.example") is True

    def test_a_different_origin_cannot_steal_an_already_claimed_id(self, registry):
        registry.register("acme-library", "https://acme.example")
        assert registry.register("acme-library", "https://impostor.example") is False
        # The original claim is untouched by the rejected attempt.
        assert registry.is_registered("acme-library", "https://acme.example") is True
        assert registry.is_registered("acme-library", "https://impostor.example") is False

    def test_unregistered_id_is_not_registered_to_anyone(self, registry):
        assert registry.is_registered("never-registered", "https://acme.example") is False


class TestGraceQuota:
    def test_grace_counts_down_then_rejects(self, registry):
        origin = "https://new-library.example"
        assert registry.consume_grace(origin) == 2
        assert registry.consume_grace(origin) == 1
        assert registry.consume_grace(origin) == 0
        assert registry.consume_grace(origin) == -1
        assert registry.consume_grace(origin) == -1  # stays exhausted, doesn't go negative-then-reset

    def test_grace_is_tracked_independently_per_origin(self, registry):
        registry.consume_grace("https://a.example")
        registry.consume_grace("https://a.example")
        # b's quota is untouched by a's usage.
        assert registry.consume_grace("https://b.example") == 2

    def test_reset_clears_both_claims_and_grace(self, registry):
        registry.register("acme-library", "https://acme.example")
        registry.consume_grace("https://new-library.example")
        registry.reset()
        assert registry.is_registered("acme-library", "https://acme.example") is False
        assert registry.consume_grace("https://new-library.example") == 2  # back to the full quota


class TestCheckWidgetRegistration:
    def test_no_library_id_is_always_untouched(self):
        # Standalone-app / direct API callers never send X-LibSync-Library.
        assert check_widget_registration(None, "https://anything.example") is None
        assert check_widget_registration("", "https://anything.example") is None

    def test_registered_pair_passes_without_consuming_grace(self, monkeypatch):
        from app import widget_registry as widget_registry_module

        test_registry = WidgetRegistry(grace_limit=1)
        test_registry.register("acme-library", "https://acme.example")
        monkeypatch.setattr(widget_registry_module, "widget_registry", test_registry)

        for _ in range(5):  # would exceed the grace_limit=1 quota if it were being consumed
            assert check_widget_registration("acme-library", "https://acme.example") is None

    def test_unregistered_pair_is_allowed_until_grace_runs_out(self, monkeypatch):
        from app import widget_registry as widget_registry_module

        test_registry = WidgetRegistry(grace_limit=2)
        monkeypatch.setattr(widget_registry_module, "widget_registry", test_registry)

        assert check_widget_registration("unregistered-lib", "https://new.example") is None
        assert check_widget_registration("unregistered-lib", "https://new.example") is None
        error = check_widget_registration("unregistered-lib", "https://new.example")
        assert error is not None
        assert "grace quota" in error

    def test_missing_origin_falls_back_to_a_shared_unknown_bucket(self, monkeypatch):
        from app import widget_registry as widget_registry_module

        test_registry = WidgetRegistry(grace_limit=1)
        monkeypatch.setattr(widget_registry_module, "widget_registry", test_registry)

        assert check_widget_registration("some-lib", None) is None
        assert check_widget_registration("some-lib", None) is not None
