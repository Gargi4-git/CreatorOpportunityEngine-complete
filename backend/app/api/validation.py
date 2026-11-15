"""Closed-loop validation: after a creator publishes a recommended video, compare actual performance with the predicted score."""
import uuid
from typing import Optional

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from scipy.stats import kendalltau, pearsonr, spearmanr

from app.db.mongodb import DatabaseUnavailable, get_db
from app.ml.embeddings import EmbeddingUnavailable, get_embedder
from app.ml.sentiment import PrototypeClassifier
from app.services import youtube_service
from app.services.progress import now

router = APIRouter(prefix="/api/validation", tags=["Validation"])
COMPONENTS = ["demand", "trend", "pain", "engagement", "freshness", "competition"]
MATURE_DAYS = 14


def _db():
    try:
        return get_db()
    except DatabaseUnavailable as exc:
        raise HTTPException(503, str(exc))


def outcome_from_ratio(ratio: float) -> float:
    """performance ratio r (video rate / creator baseline) -> 0-100 via r/(1+r): parity = 50, 3x baseline = 75."""
    return round(100 * ratio / (1 + ratio), 1)


def create_tracking(opp: dict, video_url: Optional[str] = None, plan_item_id: Optional[str] = None) -> dict:
    s = opp["scores"]
    doc = {"_id": uuid.uuid4().hex, "opportunity_id": opp["_id"], "analysis_id": opp["analysis_id"], "topic": opp["topic"],
           "predicted": {"ghostgap": s["ghostgap"], "classification": s["classification"], "components": {c: s.get(c) for c in COMPONENTS}},
           "video_url": video_url, "video_id": None, "plan_item_id": plan_item_id, "tracked_at": now(), "outcome": None, "metrics": None}
    if video_url:
        try:
            doc["video_id"] = youtube_service.extract_video_id(video_url)
        except youtube_service.YouTubeError as exc:
            raise HTTPException(422, str(exc))
    _db().validations.insert_one(doc)
    return doc


class TrackRequest(BaseModel):
    opportunity_id: str
    video_url: Optional[str] = Field(None, max_length=300)


@router.post("/track")
def track(req: TrackRequest):
    opp = _db().opportunities.find_one({"_id": req.opportunity_id})
    if not opp:
        raise HTTPException(404, "Opportunity not found.")
    return _out(create_tracking(opp, req.video_url))


class ManualMetrics(BaseModel):
    views: float = Field(ge=0)
    baseline_views: float = Field(gt=0, description="the creator's typical views for comparable videos, measured at the same video age")
    video_url: Optional[str] = Field(None, max_length=300)


@router.post("/{vid}/metrics")
def manual_metrics(vid: str, m: ManualMetrics):
    """Enter numbers by hand (no API key needed). The user is responsible for comparing at the same video age."""
    db = _db()
    doc = db.validations.find_one({"_id": vid})
    if not doc:
        raise HTTPException(404, "Tracked item not found.")
    ratio = m.views / m.baseline_views
    outcome = {"method": "manual", "ratio": round(ratio, 3), "score": outcome_from_ratio(ratio), "matured": True, "measured_at": now()}
    db.validations.update_one({"_id": vid}, {"$set": {"outcome": outcome, "metrics": {"views": m.views, "baseline_views": m.baseline_views},
                                                      **({"video_url": m.video_url} if m.video_url else {})}})
    return _out(db.validations.find_one({"_id": vid}))


@router.post("/{vid}/refresh")
def refresh(vid: str):
    """Fetch the published video's real performance from YouTube and compare with the channel's own baseline (views/day)."""
    db = _db()
    doc = db.validations.find_one({"_id": vid})
    if not doc:
        raise HTTPException(404, "Tracked item not found.")
    if not doc.get("video_id"):
        raise HTTPException(422, "No video URL attached yet. Add the published video's URL first.")
    try:
        st = youtube_service.video_stats([doc["video_id"]]).get(doc["video_id"])
        if not st:
            raise youtube_service.YouTubeError("Video not found - it may be private or deleted.")
        base = youtube_service.channel_baseline_rate(st["channel_id"], doc["video_id"])
        if not base:
            raise youtube_service.YouTubeError("Not enough other videos on this channel to compute a baseline.")
    except youtube_service.YouTubeNotConfigured as exc:
        raise HTTPException(503, {"code": "api_key_required", "message": str(exc) + " You can enter the numbers manually instead."})
    except youtube_service.YouTubeError as exc:
        raise HTTPException(422, str(exc))
    age = youtube_service._age_days(st["published_at"])
    rate = youtube_service.views_per_day(st)
    ratio = rate / base
    metrics = {"views": st["views"], "likes": st["likes"], "comments": st["comments"], "age_days": round(age, 1),
               "views_per_day": round(rate, 2), "baseline_views_per_day": round(base, 2)}
    try:   # audience reaction to the published video
        recs = youtube_service.fetch_comments(doc["video_id"], 100)
        emb = get_embedder()
        cls = PrototypeClassifier(emb).classify(emb.encode([r["text"] for r in recs]))
        n = len(cls)
        metrics["comment_sentiment"] = {"n": n, "positive": round(sum(c["sentiment"] == "positive" for c in cls) / n, 3),
                                        "negative": round(sum(c["sentiment"] == "negative" for c in cls) / n, 3),
                                        "mean_pain": round(float(np.mean([c["pain_score"] for c in cls])), 3)}
    except (youtube_service.YouTubeError, EmbeddingUnavailable):
        metrics["comment_sentiment"] = None
    outcome = {"method": "youtube_api", "ratio": round(ratio, 3), "score": outcome_from_ratio(ratio), "matured": age >= MATURE_DAYS, "measured_at": now()}
    db.validations.update_one({"_id": vid}, {"$set": {"outcome": outcome, "metrics": metrics}})
    return _out(db.validations.find_one({"_id": vid}))


@router.get("")
def list_tracked():
    return {"items": [_out(d) for d in _db().validations.find({}).sort("tracked_at", -1)]}


@router.delete("/{vid}")
def delete(vid: str):
    return {"deleted": _db().validations.delete_one({"_id": vid}).deleted_count}


def _out(d: dict) -> dict:
    d["id"] = d.pop("_id")
    return d


@router.get("/report")
def report(include_immature: bool = False):
    rows = [d for d in _db().validations.find({}) if d.get("outcome") and d["predicted"].get("ghostgap") is not None
            and (include_immature or d["outcome"].get("matured", True))]
    n = len(rows)
    out = {"n": n, "include_immature": include_immature, "points": [{"id": d["_id"], "topic": d["topic"], "predicted": d["predicted"]["ghostgap"],
           "outcome": d["outcome"]["score"], "ratio": d["outcome"]["ratio"], "classification": d["predicted"]["classification"]} for d in rows]}
    if n < 3:
        out["available"] = False
        out["reason"] = f"Track at least 3 published videos with outcomes (have {n}). Videos younger than {MATURE_DAYS} days are excluded unless you include them."
        return out
    pred = [p["predicted"] for p in out["points"]]
    outc = [p["outcome"] for p in out["points"]]
    sp, pe, ke = spearmanr(pred, outc), pearsonr(pred, outc), kendalltau(pred, outc)
    hi = [p for p in out["points"] if p["predicted"] >= 60]
    lo = [p for p in out["points"] if p["predicted"] < 60]
    beat = lambda g: round(sum(p["ratio"] > 1 for p in g) / len(g), 3) if g else None
    per = {}
    for c in COMPONENTS:
        pairs = [(d["predicted"]["components"].get(c), d["outcome"]["score"]) for d in rows if d["predicted"]["components"].get(c) is not None]
        per[c] = (round(float(spearmanr(*zip(*pairs))[0]), 3) if len(pairs) >= 3 and len({a for a, _ in pairs}) > 1 else None)
    f = lambda x: None if x is None or np.isnan(x) else round(float(x), 3)
    out.update({"available": True, "spearman": {"rho": f(sp[0]), "p_value": f(sp[1])}, "pearson": {"r": f(pe[0]), "p_value": f(pe[1])},
                "kendall_tau": f(ke[0]), "high_score_beat_baseline_rate": beat(hi), "low_score_beat_baseline_rate": beat(lo),
                "n_high": len(hi), "n_low": len(lo), "per_component_spearman": per,
                "reliable": n >= 10,
                "interpretation": ("Too few tracked videos for statistical conclusions - treat as anecdotal." if n < 10 else
                                   "Positive, significant rank correlation: higher GhostGap scores tended to precede better-performing videos." if (f(sp[0]) or 0) > 0 and (f(sp[1]) or 1) < 0.05
                                   else "No statistically significant relationship between GhostGap and outcomes in this sample.")})
    return out
