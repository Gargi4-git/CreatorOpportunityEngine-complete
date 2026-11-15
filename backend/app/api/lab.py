"""GhostGap Lab: live re-weighting, rank-sensitivity analysis, and learned weights."""
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.db.mongodb import DatabaseUnavailable, get_db
from app.ml import learned_weights, scoring, sensitivity
from app.services import analysis_loader

router = APIRouter(prefix="/api/lab", tags=["GhostGap Lab"])


def _opps(aid: Optional[str]):
    try:
        aid = aid or analysis_loader.latest_analysis_id()
        if not aid:
            raise HTTPException(404, "Run an analysis first.")
        opps = list(get_db().opportunities.find({"analysis_id": aid}))
    except DatabaseUnavailable as exc:
        raise HTTPException(503, str(exc))
    if not opps:
        raise HTTPException(404, "This analysis has no opportunities.")
    return aid, sorted(opps, key=lambda o: o.get("rank", 10**6))


@router.get("/weights")
def weights():
    return {"weights": sensitivity.default_weights(), "note": "Positive weights add to the score; competition is always a penalty."}


class RescoreRequest(BaseModel):
    analysis_id: Optional[str] = None
    weights: Dict[str, float]
    sensitivity: bool = False
    draws: int = Field(500, ge=50, le=2000)
    spread: float = Field(0.3, gt=0, le=0.9)


@router.post("/rescore")
def rescore(req: RescoreRequest):
    bad = [k for k in req.weights if k not in sensitivity.NAMES]
    if bad or any(v < 0 or v > 2 for v in req.weights.values()):
        raise HTTPException(422, "Weights must be between 0 and 2 and named: " + ", ".join(sensitivity.NAMES))
    aid, opps = _opps(req.analysis_id)
    w = {**sensitivity.default_weights(), **req.weights}
    comps = [o["scores"] for o in opps]
    results = [scoring.ghostgap(c, w) for c in comps]
    order = sorted(range(len(opps)), key=lambda i: (results[i]["score"] is None, -(results[i]["score"] or 0)))
    new_rank = {i: r for r, i in enumerate(order, 1)}
    rows = [{"id": o["_id"], "topic": o["topic"], "original_rank": o.get("rank"), "new_rank": new_rank[i], "rank_change": (o.get("rank") or 0) - new_rank[i],
             "original_score": o["scores"]["ghostgap"], "new_score": results[i]["score"], "classification": results[i]["classification"],
             "breakdown": results[i]["breakdown"]} for i, o in enumerate(opps)]
    rows.sort(key=lambda r: r["new_rank"])
    out = {"analysis_id": aid, "weights": w, "topics": rows}
    if req.sensitivity:
        mc = sensitivity.monte_carlo(comps, w, req.draws, req.spread)
        for p in mc["per_topic"]:
            p["topic"], p["id"] = opps[p["index"]]["topic"], opps[p["index"]]["_id"]
        base = sensitivity.one_at_a_time(comps, w)
        for r in base:
            for tag in ("down", "up"):
                r[tag]["top_topic"] = opps[r[tag]["top_index"]]["topic"]
        mc["baseline_top_topic"] = opps[mc["baseline_top"]]["topic"]
        out["sensitivity"] = {"monte_carlo": mc, "one_at_a_time": base}
    return out


@router.post("/learn")
def learn():
    """Fit weights from tracked-video outcomes (closed-loop validation data)."""
    try:
        rows = [{"components": v["predicted"]["components"], "outcome": v["outcome"]["score"], "default_score": v["predicted"]["ghostgap"]}
                for v in get_db().validations.find({"outcome.score": {"$ne": None}}) if v.get("outcome") and v["predicted"].get("ghostgap") is not None]
    except DatabaseUnavailable as exc:
        raise HTTPException(503, str(exc))
    return learned_weights.fit(rows)
