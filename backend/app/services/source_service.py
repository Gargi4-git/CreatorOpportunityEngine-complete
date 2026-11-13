"""Create `sources` + raw `audience_records` documents (shared by every ingestion endpoint)."""
import uuid
from typing import List, Optional

from app.db.mongodb import get_db
from app.services.progress import now


def create_source(kind: str, label: str, records: List[dict], meta: Optional[dict] = None, dataset_label: str = "live",
                  status: str = "ready") -> str:
    db = get_db()
    sid = uuid.uuid4().hex
    db.sources.insert_one({"_id": sid, "type": kind, "label": label, "dataset_label": dataset_label, "status": status,
                           "meta": meta or {}, "record_count": len(records), "created_at": now(), "error": None})
    if records:
        db.audience_records.insert_many([{**r, "_id": uuid.uuid4().hex, "source_ref": sid, "stage": "raw"} for r in records])
    return sid


def attach_records(sid: str, records: List[dict], meta: dict) -> None:
    db = get_db()
    if records:
        db.audience_records.insert_many([{**r, "_id": uuid.uuid4().hex, "source_ref": sid, "stage": "raw"} for r in records])
    db.sources.update_one({"_id": sid}, {"$set": {"status": "ready", "record_count": len(records), "meta": meta}})


def fail_source(sid: str, message: str) -> None:
    get_db().sources.update_one({"_id": sid}, {"$set": {"status": "failed", "error": message}})
