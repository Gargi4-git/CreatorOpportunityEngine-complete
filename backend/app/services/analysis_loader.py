"""Load a finished analysis (embeddings + cluster assignment) back from the database."""
from typing import Dict, List, Optional

import numpy as np

from app.db.mongodb import get_db


def latest_analysis_id() -> Optional[str]:
    a = get_db().analyses.find_one({"status": "completed"}, sort=[("completed_at", -1)])
    return a["_id"] if a else None


def load_matrix(aid: str):
    """-> (E, cluster_labels, records) ordered by embedding index. Raises LookupError if the analysis has no embeddings."""
    db = get_db()
    recs = list(db.audience_records.find({"analysis_id": aid, "stage": "analyzed"}))
    if not recs:
        raise LookupError("Analysis not found or has no analyzed records.")
    recs.sort(key=lambda r: int(r["embedding_id"].split(":")[1]))
    emb = {d["_id"]: d["vector"] for d in db.embeddings.find({"analysis_id": aid})}
    E = np.stack([np.frombuffer(emb[r["embedding_id"]], dtype=np.float32) for r in recs])
    return E, np.array([r["cluster_id"] for r in recs]), recs


def centroids(aid: str) -> Dict[int, np.ndarray]:
    E, labels, _ = load_matrix(aid)
    out = {}
    for c in sorted(set(labels.tolist()) - {-1}):
        v = E[labels == c].mean(axis=0)
        out[c] = v / (np.linalg.norm(v) or 1.0)
    return out
