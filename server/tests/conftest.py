import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.rate_limit import limiter


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Ensure each test starts with a clean rate-limit counter."""
    limiter.reset()
    yield


@pytest.fixture()
def client():
    return TestClient(app)
