"""Handles interactions with the Pinecone vector database.

The index was provisioned via `create_index_for_model` (see
pinecone-scripts/check_pinecone_index.py), which enables integrated
embedding: Pinecone embeds the query text server-side, so callers pass plain
text rather than a precomputed vector.
"""

from pinecone import Pinecone

from app.config import PINECONE_API_KEY

INDEX_NAME = "libsync-policy-index"
NAMESPACE = "ns1"

_pinecone_client: Pinecone | None = None


def _get_index():
    global _pinecone_client
    if _pinecone_client is None:
        _pinecone_client = Pinecone(api_key=PINECONE_API_KEY)
    return _pinecone_client.Index(INDEX_NAME)


def search_pinecone(text: str, top_k: int = 5) -> dict:
    """Search the Pinecone index for policy chunks matching a natural-language query.

    Raises:
        ValueError: If the query text is not provided.
        RuntimeError: If the search fails.
    """
    if not text or not text.strip():
        raise ValueError("Query text is required.")

    try:
        index = _get_index()
        response = index.search(
            namespace=NAMESPACE,
            top_k=top_k,
            inputs={"text": text},
            fields=["chunk_text", "category"],
        )
        return {
            "matches": [
                {
                    "id": hit.id,
                    "score": hit.score,
                    "text": hit.fields.get("chunk_text"),
                    "category": hit.fields.get("category"),
                }
                for hit in response.result.hits
            ]
        }
    except ValueError:
        raise
    except Exception as error:
        print("Error searching Pinecone:", error)
        raise RuntimeError("Failed to search Pinecone index.") from error
