"""Handles interactions with the Pinecone vector database."""

from pinecone import Pinecone

from app.config import PINECONE_API_KEY

INDEX_NAME = "libsync-policy-index"

_pinecone_client: Pinecone | None = None


def _get_index():
    global _pinecone_client
    if _pinecone_client is None:
        _pinecone_client = Pinecone(api_key=PINECONE_API_KEY)
    return _pinecone_client.Index(INDEX_NAME)


def query_pinecone(vector: list[float], top_k: int = 5) -> dict:
    """Query the Pinecone index with a given vector to find the most similar items.

    Raises:
        ValueError: If the query vector is not provided.
        RuntimeError: If the query fails.
    """
    if not vector:
        raise ValueError("Query vector is required.")

    try:
        index = _get_index()
        response = index.query(
            vector=vector,
            top_k=top_k,
            include_values=True,
            include_metadata=True,
        )
        return response.to_dict() if hasattr(response, "to_dict") else dict(response)
    except ValueError:
        raise
    except Exception as error:
        print("Error querying Pinecone:", error)
        raise RuntimeError("Failed to query Pinecone index.") from error
