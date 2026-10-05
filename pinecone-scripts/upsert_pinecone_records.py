"""Syncs the library policy records into the Pinecone index: inserts missing records and
updates existing ones whose text or category changed (unchanged records are skipped).

It used to skip every id already in the index, so edits to existing records (e.g. pol7's color
price, pol9's turnaround time) silently never reached the live index."""

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
    {"_id": "pol7", "chunk_text": "Printing and photocopying services are available. Black and white copies are $0.10 per page, color copies are $0.50 per page.", "category": "services"},
    {"_id": "pol8", "chunk_text": "The library is not responsible for lost or stolen personal items. Please keep your valuables with you.", "category": "conduct"},
    {"_id": "pol9", "chunk_text": "Inter-library loan services are available for materials not found in our collection. Request forms are at the circulation desk, and requests typically take 1-2 weeks to arrive.", "category": "lending"},
    {"_id": "pol10", "chunk_text": "Food and drink are permitted only in designated lounge areas. Please dispose of all trash properly.", "category": "conduct"},
    {"_id": "pol11", "chunk_text": "Overdue fines are capped at $5.00 per item, and no further fines accrue once that cap is reached.", "category": "fines"},
    {"_id": "pol12", "chunk_text": "Lost or damaged items are charged at full replacement cost plus a $5.00 processing fee.", "category": "fines"},
    {"_id": "pol13", "chunk_text": "Fines can be paid online, at the self-checkout kiosks, or in person at the circulation desk. We accept cash, card, and check.", "category": "fines"},
    {"_id": "pol14", "chunk_text": "Items may be renewed up to three times online or by phone, as long as no one else has placed a hold on them.", "category": "lending"},
    {"_id": "pol15", "chunk_text": "Holds can be placed on any item in the catalog, including titles currently checked out. You'll get an email or text when it's ready for pickup.", "category": "lending"},
    {"_id": "pol16", "chunk_text": "Held items are kept on the reserve shelf for 7 days after the pickup notification before being returned to circulation.", "category": "lending"},
    {"_id": "pol17", "chunk_text": "Children under 13 need a parent or guardian's signature to register for a library card. Kids get their own card, not a shared family card.", "category": "membership"},
    {"_id": "pol18", "chunk_text": "A replacement card for a lost or stolen library card costs $2.00. Report a lost card immediately to avoid being charged for items borrowed on it.", "category": "membership"},
    {"_id": "pol19", "chunk_text": "Library cards must be renewed annually. Bring a valid photo ID to renew in person, or renew online if your account is in good standing.", "category": "membership"},
    {"_id": "pol20", "chunk_text": "Free public WiFi is available throughout the building, no library card required. Portable WiFi hotspots can be checked out by cardholders for up to one week.", "category": "computer use"},
    {"_id": "pol21", "chunk_text": "3D printing is available by appointment. Print jobs are charged at $0.10 per gram of filament used, with a $5.00 maximum per job for cardholders.", "category": "services"},
    {"_id": "pol22", "chunk_text": "Meeting room bookings are limited to two hours per group per week and must be made at least 48 hours in advance.", "category": "facilities"},
    {"_id": "pol23", "chunk_text": "Study rooms seat up to six people and can be reserved online for up to two hours per day, first-come first-served after that.", "category": "facilities"},
    {"_id": "pol24", "chunk_text": "The library offers free notary services by appointment on weekday afternoons. Bring a valid photo ID.", "category": "services"},
    {"_id": "pol25", "chunk_text": "Free tax preparation assistance is available every filing season, typically February through mid-April, in partnership with local volunteers.", "category": "services"},
    {"_id": "pol26", "chunk_text": "Voter registration forms are available at the circulation desk year-round, and library staff can help patrons check their registration status.", "category": "services"},
    {"_id": "pol27", "chunk_text": "Museum and cultural passes to local attractions can be checked out with a library card for one week at a time, subject to availability.", "category": "lending"},
    {"_id": "pol28", "chunk_text": "The library hosts free digital literacy workshops, including 'Intro to Canva' and 'Online Job Searching,' on a monthly rotating schedule. Sign up at the front desk or online.", "category": "programs"},
    {"_id": "pol29", "chunk_text": "Homework help and free tutoring for K-12 students is available after school on weekdays in the children's section.", "category": "programs"},
    {"_id": "pol30", "chunk_text": "ESL (English as a Second Language) conversation groups meet weekly and are open to all skill levels, no registration required.", "category": "programs"},
    {"_id": "pol31", "chunk_text": "Assistive technology, including screen readers and large-print keyboards, is available on request at any public computer station.", "category": "accessibility"},
    {"_id": "pol32", "chunk_text": "Curbside pickup is available for patrons who are unable to enter the building. Call ahead or request it when placing a hold online.", "category": "accessibility"},
    {"_id": "pol33", "chunk_text": "Donations of gently used books are accepted at the circulation desk. The library cannot provide tax-deduction valuations for donated items.", "category": "services"},
    {"_id": "pol34", "chunk_text": "Volunteer opportunities include shelving, program assistance, and the Friends of the Library book sale group. Apply online or ask at the front desk.", "category": "services"},
]


def needs_upsert(record: dict, existing_vectors: dict) -> bool:
    """True if the record is missing from the index, or its stored text/category differs."""
    live = existing_vectors.get(record["_id"])
    if live is None:
        return True
    stored = live.metadata or {}
    return stored.get("chunk_text") != record["chunk_text"] or stored.get("category") != record["category"]


def upsert_records() -> None:
    pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY", "PINECONE_API_KEY"))

    try:
        index = pc.Index(name=INDEX_NAME)
        record_ids = [record["_id"] for record in RECORDS]
        fetch_response = index.fetch(ids=record_ids, namespace=NAMESPACE)

        records_to_upsert = [record for record in RECORDS if needs_upsert(record, fetch_response.vectors)]

        if records_to_upsert:
            new_count = sum(1 for record in records_to_upsert if record["_id"] not in fetch_response.vectors)
            print(
                f"Upserting {len(records_to_upsert)} records into index '{INDEX_NAME}' "
                f"({new_count} new, {len(records_to_upsert) - new_count} changed): "
                f"{', '.join(record['_id'] for record in records_to_upsert)}"
            )
            index.upsert_records(namespace=NAMESPACE, records=records_to_upsert)
            print("Records upserted successfully.")
        else:
            print("Index already matches the seed records. No upsert needed.")
    except Exception as error:
        print("An error occurred during the upsert process:", error)
        sys.exit(1)


if __name__ == "__main__":
    upsert_records()
