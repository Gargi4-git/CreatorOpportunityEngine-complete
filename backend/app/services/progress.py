"""Analysis lifecycle + progress tracking (polled by the frontend via GET /api/analysis/{id})."""
import uuid
from datetime import datetime, timezone
from typing import List

from app.db.mongodb import get_db

STEPS = [
    ("fetch", "Fetching audience conversations"),
    ("clean", "Cleaning data"),
    ("multimodal", "Unifying multimodal signals"),
    ("embed", "Generating semantic embeddings"),
    ("cluster", "Finding audience clusters"),
    ("intent", "Analyzing audience intent"),
    ("demand", "Detecting demand"),
    ("trend", "Detecting trends"),
    ("competition", "Analyzing competition"),
    ("ghostgap", "Running GhostGap"),
    ("recommend", "Generating recommendations"),
    ("finalize", "Finalizing insights"),
]
KEYS = [k for k, _ in STEPS]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_analysis(source_ids: List[str]) -> str:
    aid = uuid.uuid4().hex
    get_db().analyses.insert_one({
        "_id": aid, "source_ids": source_ids, "status": "queued", "created_at": now(), "progress": 0,
        "steps": [{"key": k, "label": l, "status": "pending", "detail": None} for k, l in STEPS],
        "error": None, "summary": None})
    return aid


def step(aid: str, key: str, status: str, detail: str = None) -> None:
    idx = KEYS.index(key)
    done = status != "running"
    get_db().analyses.update_one({"_id": aid}, {"$set": {
        f"steps.{idx}.status": status, f"steps.{idx}.detail": detail, "status": "running",
        "progress": round((idx + (1 if done else 0.4)) / len(STEPS) * 100)}})


def fail(aid: str, message: str) -> None:
    get_db().analyses.update_one({"_id": aid}, {"$set": {"status": "failed", "error": message}})
