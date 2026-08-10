"""Unit tests for the Tier 6 per-origin rate-limit key function
(app/rate_limit.py's get_origin_or_ip) — pure logic, no HTTP layer. Route
wiring (stacked @limiter.limit(...) decorators on /agent and /chat) is
exercised indirectly by every other test in test_agent_endpoint.py and
test_chat.py, which all pass through both limits on each request."""

from starlette.requests import Request

from app.rate_limit import get_origin_or_ip


def _make_request(headers: dict[str, str]) -> Request:
    encoded_headers = [(key.lower().encode(), value.encode()) for key, value in headers.items()]
    scope = {"type": "http", "headers": encoded_headers, "client": ("192.0.2.1", 12345)}
    return Request(scope)


class TestGetOriginOrIp:
    def test_uses_the_origin_header_when_present(self):
        request = _make_request({"origin": "https://library.example"})
        assert get_origin_or_ip(request) == "https://library.example"

    def test_falls_back_to_remote_address_when_origin_is_absent(self):
        # Non-browser callers (curl, server-to-server) rarely send Origin.
        request = _make_request({})
        assert get_origin_or_ip(request) == "192.0.2.1"

    def test_different_origins_produce_different_keys(self):
        a = _make_request({"origin": "https://library-a.example"})
        b = _make_request({"origin": "https://library-b.example"})
        assert get_origin_or_ip(a) != get_origin_or_ip(b)
