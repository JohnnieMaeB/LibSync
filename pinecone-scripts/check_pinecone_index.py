"""Creates the LibSync policy index if it doesn't already exist."""

import os
import sys

from pinecone import Pinecone

INDEX_NAME = "libsync-policy-index"


def check_and_create_index() -> None:
    pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY", "PINECONE_API_KEY"))

    try:
        existing_indexes = pc.list_indexes()
        index_exists = any(index.name == INDEX_NAME for index in existing_indexes.indexes)

        if index_exists:
            print(f"Index '{INDEX_NAME}' already exists.")
            return

        print(f"Index '{INDEX_NAME}' does not exist. Creating...")
        pc.create_index_for_model(
            name=INDEX_NAME,
            cloud="aws",
            region="us-east-1",
            embed={
                "model": "llama-text-embed-v2",
                "field_map": {"text": "chunk_text"},
            },
        )
        print(f"Index '{INDEX_NAME}' created successfully.")
    except Exception as error:
        print("An error occurred:", error)
        sys.exit(1)


if __name__ == "__main__":
    check_and_create_index()
