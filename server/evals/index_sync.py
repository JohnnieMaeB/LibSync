"""Pre-flight check: the live policy index must match the seed file.

Two real incidents motivated this (October 2026): the index held 10 of the
seed file's 34 records, and later two *existing* records (pol7, pol9) still
carried their original text after the seed file was edited, because the
upsert script only inserted IDs it didn't find. Both made correct agent
behavior look like failures, or hid missing facts behind an honest "the
policy doesn't say."

This check is deterministic and costs no LLM tokens, so the eval runner runs
it first and stops with a precise message instead of spending a full suite on
answers that can't be right.
"""

import importlib.util
from pathlib import Path
from types import ModuleType

from app.services.pinecone_service import DEFAULT_NAMESPACE, _get_index

SEED_PATH = Path(__file__).resolve().parents[2] / "pinecone-scripts" / "upsert_pinecone_records.py"


def load_seed_module() -> ModuleType:
    """Loads the seed script by path (it lives in a separate uv project, so it
    isn't importable as a package)."""
    spec = importlib.util.spec_from_file_location("libsync_seed_records", SEED_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def diff_index(seed_records: list[dict], live_fields: dict[str, dict | None]) -> tuple[list[str], list[str]]:
    """Returns (missing_ids, stale_ids). `live_fields` maps a record id to its
    stored `chunk_text`/`category` fields, or None if the id isn't in the index."""
    missing, stale = [], []
    for record in seed_records:
        live = live_fields.get(record["_id"])
        if live is None:
            missing.append(record["_id"])
        elif live.get("chunk_text") != record["chunk_text"] or live.get("category") != record["category"]:
            stale.append(record["_id"])
    return missing, stale


def check_index_in_sync() -> tuple[list[str], list[str]]:
    seed_records = load_seed_module().RECORDS
    fetched = _get_index().fetch(ids=[r["_id"] for r in seed_records], namespace=DEFAULT_NAMESPACE).vectors
    live = {record_id: (vector.metadata or {}) for record_id, vector in fetched.items()}
    return diff_index(seed_records, live)
