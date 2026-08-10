"""Tests for POST /widget/register (Tier 6's lightweight allowlist step)."""

import pytest

from app.widget_registry import widget_registry


@pytest.fixture(autouse=True)
def reset_widget_registry():
    widget_registry.reset()
    yield
    widget_registry.reset()


class TestWidgetRegisterEndpoint:
    def test_registers_a_new_library_id(self, client):
        response = client.post(
            "/widget/register",
            json={"library_id": "acme-library"},
            headers={"Origin": "https://acme.example"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body == {"library_id": "acme-library", "origin": "https://acme.example", "registered": True}
        assert widget_registry.is_registered("acme-library", "https://acme.example")

    def test_re_registering_the_same_origin_succeeds(self, client):
        client.post("/widget/register", json={"library_id": "acme-library"}, headers={"Origin": "https://acme.example"})
        response = client.post(
            "/widget/register", json={"library_id": "acme-library"}, headers={"Origin": "https://acme.example"}
        )
        assert response.status_code == 200

    def test_a_different_origin_cannot_claim_an_already_registered_id(self, client):
        client.post("/widget/register", json={"library_id": "acme-library"}, headers={"Origin": "https://acme.example"})
        response = client.post(
            "/widget/register", json={"library_id": "acme-library"}, headers={"Origin": "https://impostor.example"}
        )
        assert response.status_code == 409

    def test_missing_library_id_is_a_400(self, client):
        response = client.post("/widget/register", json={}, headers={"Origin": "https://acme.example"})
        assert response.status_code == 400

    def test_missing_origin_header_is_a_400(self, client):
        response = client.post("/widget/register", json={"library_id": "acme-library"})
        assert response.status_code == 400
