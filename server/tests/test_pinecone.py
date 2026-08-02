import pytest

from app.routers import pinecone_query


def fake_search_pinecone(text, top_k=5):
    return {
        "matches": [
            {
                "id": "pol3",
                "score": 0.98,
                "text": "A fine of $0.25 per day is charged for overdue items.",
                "category": "fines",
            }
        ]
    }


def failing_search_pinecone(text, top_k=5):
    raise RuntimeError("Mocked Pinecone failure")


@pytest.fixture()
def mock_pinecone(monkeypatch):
    monkeypatch.setattr(pinecone_query, "search_pinecone", fake_search_pinecone)


@pytest.fixture()
def failing_pinecone(monkeypatch):
    monkeypatch.setattr(pinecone_query, "search_pinecone", failing_search_pinecone)


class TestQueryEndpoint:
    def test_returns_results_for_valid_query(self, client, mock_pinecone):
        response = client.post("/api/query", json={"text": "how much are late fees?"})
        assert response.status_code == 200
        body = response.json()
        assert "matches" in body
        assert isinstance(body["matches"], list)
        assert body["matches"][0]["text"] == "A fine of $0.25 per day is charged for overdue items."

    def test_returns_results_with_top_k(self, client, mock_pinecone):
        response = client.post("/api/query", json={"text": "late fees", "topK": 10})
        assert response.status_code == 200
        assert isinstance(response.json()["matches"], list)

    def test_returns_400_if_text_missing(self, client, mock_pinecone):
        response = client.post("/api/query", json={})
        assert response.status_code == 400
        assert response.json() == {"error": "Query text is required."}

    def test_handles_pinecone_errors_and_returns_500(self, client, failing_pinecone):
        response = client.post("/api/query", json={"text": "late fees"})
        assert response.status_code == 500
        assert response.json() == {"error": "Failed to search Pinecone index."}
