"""Upserts the library policy records into the Pinecone index (skips ones that already exist)."""

import os
import sys

from pinecone import Pinecone

INDEX_NAME = "libsync-policy-index"
NAMESPACE = "ns1"

RECORDS = [
    {"_id": "pol1", "chunk_text": "Library cards are free to all residents. Please provide proof of address to register.", "category": "membership"},
    {"_id": "pol2", "chunk_text": "Books may be borrowed for a period of three weeks. Renewals are available online.", "category": "lending"},
    {"_id": "pol3", "chunk_text": "A fine of $0.25 per day is charged for overdue items. This applies to all books and media.", "category": "fines"},
    {"_id": "pol4", "chunk_text": "Public computers are available for use for up to two hours per day. A library card is required to log in.", "category": "computer use"},
    {"_id": "pol5", "chunk_text": "The library's meeting rooms can be booked for non-commercial use. Please inquire at the front desk for availability.", "category": "facilities"},
    {"_id": "pol6", "chunk_text": "Quiet study areas are designated on the second floor. Please be respectful of other patrons.", "category": "conduct"},
    {"_id": "pol7", "chunk_text": "Printing and photocopying services are available. Black and white copies are $0.10 per page.", "category": "services"},
    {"_id": "pol8", "chunk_text": "The library is not responsible for lost or stolen personal items. Please keep your valuables with you.", "category": "conduct"},
    {"_id": "pol9", "chunk_text": "Inter-library loan services are available for materials not found in our collection. Request forms are at the circulation desk.", "category": "lending"},
    {"_id": "pol10", "chunk_text": "Food and drink are permitted only in designated lounge areas. Please dispose of all trash properly.", "category": "conduct"},
]


def upsert_records() -> None:
    pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY", "PINECONE_API_KEY"))

    try:
        index = pc.Index(name=INDEX_NAME)
        record_ids = [record["_id"] for record in RECORDS]
        fetch_response = index.fetch(ids=record_ids, namespace=NAMESPACE)

        existing_ids = set(fetch_response.vectors.keys())
        records_to_upsert = [record for record in RECORDS if record["_id"] not in existing_ids]

        if records_to_upsert:
            print(f"Upserting {len(records_to_upsert)} new records into index '{INDEX_NAME}'...")
            index.upsert_records(namespace=NAMESPACE, records=records_to_upsert)
            print("Records upserted successfully.")
        else:
            print("All records already exist in the index. No upsert needed.")
    except Exception as error:
        print("An error occurred during the upsert process:", error)
        sys.exit(1)


if __name__ == "__main__":
    upsert_records()
