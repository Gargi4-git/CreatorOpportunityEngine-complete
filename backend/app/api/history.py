"""Analysis history, side-by-side comparison, and topic trajectories over time for the same source (e.g. one channel)."""
from typing import Dict, List, Optional

import numpy as np
from fastapi import APIRouter, HTTPException

from app.db.mongodb import DatabaseUnavailable, get_db
from app.services import analysis_loader

router = APIRouter(prefix="/api/history", tags=["History"])


def _db():
    try:
        return get_db()
    except DatabaseUnavailable as exc:
        raise HTTPException(503, str(exc))


def _brief(a: dict, db) -> dict:
    S = a.get("summary") or {}
    top = db.opportunities.find_one({"analysis_id": a["_id"], "rank": 1})
    labels = [s["label"] for s in db.sources.find({"_id": {"$in": a["source_ids"]}})]
    return {"id": a["_id"], "created_at": a["created_at"], "completed_at": a.get("completed_at"), "status": a["status"],
            "label": " + ".join(labels) or a["_id"][:8], "source_key": a.get("source_key"), "options": a.get("options", {}),
            "comments": S.get("audience_comments"), "topics": (S.get("clustering") or {}).get("clusters"), "avg_ghostgap": S.get("avg_opportunity_score"),
            "avg_trend": S.get("avg_trend"), "top_topic": top["topic"] if top else None, "top_score": top["scores"]["ghostgap"] if top else None,
            "embedding_model": S.get("embedding_model")}


@router.get("")
def history():
    db = _db()
    items = [_brief(a, db) for a in db.analyses.find({}).sort("created_at", -1).limit(200)]
    keys: Dict[str, int] = {}
    for i in items:
        if i["status"] == "completed" and i["source_key"]:
            keys[i["source_key"]] = keys.get(i["source_key"], 0) + 1
    return {"analyses": items, "trackable_sources": [{"key": k, "analyses": n} for k, n in keys.items() if n >= 2]}


def match_topics(ca: Dict[int, np.ndarray], cb: Dict[int, np.ndarray], threshold: float):
    """Greedy one-to-one matching of cluster centroids by cosine similarity."""
    pairs = sorted(((float(ca[i] @ cb[j]), i, j) for i in ca for j in cb), reverse=True)
    used_a, used_b, out = set(), set(), []
    for sim, i, j in pairs:
        if sim < threshold:
            break
        if i in used_a or j in used_b:
            continue
        used_a.add(i); used_b.add(j); out.append((i, j, sim))
    return out


@router.get("/compare")
def compare(a: str, b: str, threshold: float = 0.5):
    db = _db()
    A, B = db.analyses.find_one({"_id": a}), db.analyses.find_one({"_id": b})
    if not A or not B or A["status"] != "completed" or B["status"] != "completed":
        raise HTTPException(404, "Both analyses must exist and be completed.")
    ma, mb = (A["summary"] or {}).get("embedding_model"), (B["summary"] or {}).get("embedding_model")
    if ma != mb:
        raise HTTPException(422, f"These analyses used different embedding models ({ma} vs {mb}); topics cannot be compared across them.")
    oa = {o["cluster_id"]: o for o in db.opportunities.find({"analysis_id": a})}
    ob = {o["cluster_id"]: o for o in db.opportunities.find({"analysis_id": b})}
    ca, cb = analysis_loader.centroids(a), analysis_loader.centroids(b)
    pairs = match_topics({k: v for k, v in ca.items() if k in oa}, {k: v for k, v in cb.items() if k in ob}, threshold)
    slim = lambda o: {"id": o["_id"], "topic": o["topic"], "ghostgap": o["scores"]["ghostgap"], "demand": o["scores"]["demand"], "trend": o["scores"]["trend"],
                      "pain": o["scores"]["pain"], "competition": o["scores"]["competition"], "evidence": o["evidence_count"], "platforms": o["platform_share"]}
    d = lambda x, y: None if x is None or y is None else round(y - x, 1)
    matched = [{"similarity": round(s, 3), "a": slim(oa[i]), "b": slim(ob[j]),
                "delta": {k: d(oa[i]["scores"][k], ob[j]["scores"][k]) for k in ("ghostgap", "demand", "trend", "pain", "competition")} |
                         {"evidence": ob[j]["evidence_count"] - oa[i]["evidence_count"]}} for i, j, s in pairs]
    matched.sort(key=lambda m: -(m["b"]["ghostgap"] or 0))
    return {"a": _brief(A, db) | {"summary": A["summary"]}, "b": _brief(B, db) | {"summary": B["summary"]}, "threshold": threshold,
            "matched": matched, "only_a": [slim(oa[i]) for i in oa if i not in {p[0] for p in pairs}],
            "only_b": [slim(ob[j]) for j in ob if j not in {p[1] for p in pairs}],
            "note": "Topics are matched by cosine similarity of cluster centroids; lower the threshold to match more loosely."}


@router.get("/series")
def series(source_key: str, threshold: float = 0.5, top: int = 6):
    """Follow the latest analysis' top topics backwards through earlier analyses of the same source (same channel / subreddit / file)."""
    db = _db()
    runs = list(db.analyses.find({"source_key": source_key, "status": "completed"}).sort("completed_at", 1))
    if len(runs) < 2:
        raise HTTPException(404, "Need at least two completed analyses of the same source.")
    models = {(r["summary"] or {}).get("embedding_model") for r in runs}
    if len(models) > 1:
        runs = [r for r in runs if (r["summary"] or {}).get("embedding_model") == (runs[-1]["summary"] or {}).get("embedding_model")]
    opps = [{o["cluster_id"]: o for o in db.opportunities.find({"analysis_id": r["_id"]})} for r in runs]
    cents = [analysis_loader.centroids(r["_id"]) for r in runs]
    last = opps[-1]
    tracked = sorted(last.values(), key=lambda o: o.get("rank", 99))[:top]
    out = []
    for o in tracked:
        cur, line = cents[-1][o["cluster_id"]], []
        for k in range(len(runs) - 1, -1, -1):
            match = None
            if k == len(runs) - 1:
                match = o
            else:
                cand = {cid: c for cid, c in cents[k].items() if cid in opps[k]}
                best = max(cand.items(), key=lambda kv: float(cur @ kv[1]), default=None)
                if best and float(cur @ best[1]) >= threshold:
                    match, cur = opps[k][best[0]], best[1]
            line.append({"analysis_id": runs[k]["_id"], "date": runs[k].get("completed_at"), "ghostgap": match["scores"]["ghostgap"] if match else None,
                         "demand": match["scores"]["demand"] if match else None, "evidence": match["evidence_count"] if match else None})
        out.append({"topic": o["topic"], "points": line[::-1]})
    return {"source_key": source_key, "analyses": [{"id": r["_id"], "date": r.get("completed_at")} for r in runs], "topics": out}
