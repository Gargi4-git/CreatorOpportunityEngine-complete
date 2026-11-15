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


def source_key(source_ids: List[str]) -> str:
    """Stable identity of what was analysed (channel / video / subreddit / file) so analyses can be tracked over time."""
    db = get_db()
    keys = []
    for s in db.sources.find({"_id": {"$in": source_ids}}):
        m = s.get("meta") or {}
        if s["type"] == "youtube" and (m.get("video", {}).get("channel_id") or m.get("channel", {}).get("channel_id")):
            keys.append("youtube:channel:" + (m.get("video", {}).get("channel_id") or m["channel"]["channel_id"]))
        elif s["type"] == "reddit":
            keys.append("reddit:" + str(m.get("subreddit")))
        else:
            keys.append(f"{s['type']}:{s['label']}")
    return " + ".join(sorted(set(keys)))


def create_analysis(source_ids: List[str], options: dict = None) -> str:
    aid = uuid.uuid4().hex
    get_db().analyses.insert_one({
        "_id": aid, "source_ids": source_ids, "options": options or {}, "source_key": source_key(source_ids), "status": "queued", "created_at": now(), "progress": 0,
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
