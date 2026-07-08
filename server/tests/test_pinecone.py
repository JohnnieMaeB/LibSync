import pytest

from app.routers import pinecone_query


def fake_query_pinecone(vector, top_k=5):
    return {
        "matches": [
            {
                "id": "1",
                "score": 0.98,
                "values": [0.1, 0.2, 0.3],
                "metadata": {"text": "Mocked search result"},
            }
        ]
    }


def failing_query_pinecone(vector, top_k=5):
    raise RuntimeError("Mocked Pinecone failure")


@pytest.fixture()
def mock_pinecone(monkeypatch):
    monkeypatch.setattr(pinecone_query, "query_pinecone", fake_query_pinecone)


@pytest.fixture()
def failing_pinecone(monkeypatch):
    monkeypatch.setattr(pinecone_query, "query_pinecone", failing_query_pinecone)


class TestQueryEndpoint:
    def test_returns_results_for_valid_query(self, client, mock_pinecone):
        response = client.post("/api/query", json={"vector": [0.1, 0.2, 0.3]})
        assert response.status_code == 200
        body = response.json()
        assert "matches" in body
        assert isinstance(body["matches"], list)

    def test_returns_results_with_top_k(self, client, mock_pinecone):
        response = client.post("/api/query", json={"vector": [0.1, 0.2, 0.3], "topK": 10})
        assert response.status_code == 200
        assert isinstance(response.json()["matches"], list)

    def test_returns_400_if_vector_missing(self, client, mock_pinecone):
        response = client.post("/api/query", json={})
        assert response.status_code == 400
        assert response.json() == {"error": "Query vector is required."}

    def test_handles_pinecone_errors_and_returns_500(self, client, failing_pinecone):
        response = client.post("/api/query", json={"vector": [0.1, 0.2, 0.3]})
        assert response.status_code == 500
        assert response.json() == {"error": "Failed to query Pinecone index."}
