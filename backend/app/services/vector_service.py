"""Vector store: FAISS (inner product on L2-normalised vectors = cosine). Falls back to NumPy brute force if faiss is absent.
Canonical embeddings live in MongoDB (`embeddings`); the index is rebuilt from there if the cache is missing."""
import json
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from app.db.mongodb import get_db

try:
    import faiss  # type: ignore
    HAVE_FAISS = True
except Exception:
    faiss = None
    HAVE_FAISS = False

DIR = Path("data/vector")
_cache: Dict[str, dict] = {}


def backend_name() -> str:
    return "faiss" if HAVE_FAISS else "numpy-bruteforce"


def build_index(analysis_id: str, E: np.ndarray, embedding_ids: List[str]) -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    np.save(DIR / f"{analysis_id}.npy", E.astype(np.float32))
    (DIR / f"{analysis_id}.json").write_text(json.dumps(embedding_ids))
    _cache.pop(analysis_id, None)


def _load(analysis_id: str) -> Optional[dict]:
    if analysis_id in _cache:
        return _cache[analysis_id]
    npy, js = DIR / f"{analysis_id}.npy", DIR / f"{analysis_id}.json"
    if npy.exists() and js.exists():
        E, ids = np.load(npy), json.loads(js.read_text())
    else:  # rebuild from MongoDB
        docs = list(get_db().embeddings.find({"analysis_id": analysis_id}))
        if not docs:
            return None
        docs.sort(key=lambda d: int(d["_id"].split(":")[1]))
        E = np.stack([np.frombuffer(d["vector"], dtype=np.float32) for d in docs])
        ids = [d["_id"] for d in docs]
    index = None
    if HAVE_FAISS:
        index = faiss.IndexFlatIP(E.shape[1])
        index.add(np.ascontiguousarray(E, dtype=np.float32))
    _cache[analysis_id] = {"E": E, "ids": ids, "index": index}
    return _cache[analysis_id]


def search_vector(analysis_id: str, vec: np.ndarray, k: int = 10) -> List[dict]:
    st = _load(analysis_id)
    if st is None:
        return []
    k = min(k, len(st["ids"]))
    q = np.ascontiguousarray(vec.reshape(1, -1), dtype=np.float32)
    if st["index"] is not None:
        scores, idx = st["index"].search(q, k)
        pairs = list(zip(idx[0].tolist(), scores[0].tolist()))
    else:
        sims = st["E"] @ q[0]
        top = np.argsort(-sims)[:k]
        pairs = [(int(i), float(sims[i])) for i in top]
    return [{"embedding_id": st["ids"][i], "score": round(s, 4)} for i, s in pairs if i >= 0]


def semantic_search(query: str, analysis_id: str, k: int = 10) -> List[dict]:
    from app.ml.embeddings import get_embedder
    hits = search_vector(analysis_id, get_embedder().encode([query])[0], k)
    docs = {d["embedding_id"]: d for d in get_db().audience_records.find(
        {"analysis_id": analysis_id, "embedding_id": {"$in": [h["embedding_id"] for h in hits]}})}
    out = []
    for h in hits:
        d = docs.get(h["embedding_id"])
        if d:
            out.append({"text": d["text"], "similarity": h["score"], "platform": d["source"], "modality": d["modality"],
                        "cluster_id": d.get("cluster_id"), "intent": d.get("intent"), "sentiment": d.get("sentiment"),
                        "likes": d["engagement"]["likes"], "timestamp": d.get("timestamp")})
    return out
