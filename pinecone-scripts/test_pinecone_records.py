"""Smoke-tests the Pinecone index with a reranked search query and prints index stats."""

import os
import sys

from pinecone import Pinecone

INDEX_NAME = "libsync-policy-index"
NAMESPACE = "ns1"
QUERY = "Famous historical structures and monuments"


def test_index() -> None:
    pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY", "PINECONE_API_KEY"))

    try:
        index = pc.Index(name=INDEX_NAME)
        print(f"Querying index '{INDEX_NAME}' with query: '{QUERY}'")

        reranked_results = index.search_records(
            namespace=NAMESPACE,
            query={"top_k": 5, "inputs": {"text": QUERY}},
            rerank={"model": "bge-reranker-v2-m3", "top_n": 5, "rank_fields": ["chunk_text"]},
        )
        print("Reranked query results:", reranked_results)

        stats = index.describe_index_stats()
        print("Index stats:", stats)
    except Exception as error:
        print("An error occurred during the test:", error)
        sys.exit(1)


if __name__ == "__main__":
    test_index()
