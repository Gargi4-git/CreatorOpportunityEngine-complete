"""GET /api/analytics/overview - every number the Overview and Analytics pages show is computed here from stored data."""
from collections import Counter
from typing import Optional

from fastapi import APIRouter, HTTPException

from app.db.mongodb import DatabaseUnavailable, get_db
from app.ml.trends import trend_for

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])
BINS = [(0, 20), (20, 40), (40, 60), (60, 80), (80, 101)]


@router.get("/overview")
def overview(analysis_id: Optional[str] = None):
    try:
        db = get_db()
        a = db.analyses.find_one({"_id": analysis_id}) if analysis_id else db.analyses.find_one({"status": "completed"}, sort=[("completed_at", -1)])
        if not a or a.get("status") != "completed":
            return {"has_data": False, "message": "No analysis yet"}
        aid = a["_id"]
        opps = list(db.opportunities.find({"analysis_id": aid}))
        recs = list(db.audience_records.find({"analysis_id": aid, "stage": "analyzed"}))
        sources = list(db.sources.find({"_id": {"$in": a["source_ids"]}}))
    except DatabaseUnavailable as exc:
        raise HTTPException(503, str(exc))

    opps.sort(key=lambda o: -(o["scores"]["ghostgap"] or -1))
    S = a["summary"]
    all_ts = [r["timestamp"] for r in recs]
    overall = trend_for(all_ts, all_ts)
    gg = [o["scores"]["ghostgap"] for o in opps if o["scores"]["ghostgap"] is not None]
    comp_pts = [{"topic": o["topic"], "demand": o["scores"]["demand"], "competition": o["scores"]["competition"],
                 "ghostgap": o["scores"]["ghostgap"], "quadrant": o["scores"]["quadrant"], "evidence": o["evidence_count"], "id": o["_id"]}
                for o in opps if o["scores"]["competition"] is not None and o["scores"]["demand"] is not None]
    return {
        "has_data": True, "analysis_id": aid, "completed_at": a.get("completed_at"),
        "dataset_labels": sorted({s.get("dataset_label", "live") for s in sources}),
        "source_labels": [s["label"] for s in sources],
        "summary": S,
        "topic_distribution": [{"topic": o["topic"], "count": o["evidence_count"]} for o in opps],
        "demand_by_topic": [{"topic": o["topic"], "demand": o["scores"]["demand"]} for o in opps],
        "trend_over_time": ({"available": True, "granularity": overall["granularity"], "series": overall["series"]}
                            if overall["available"] else {"available": False, "reason": "Not enough timestamped data to calculate trends."}),
        "topic_trends": [{"topic": o["topic"], "series": o["trend"]["series"]} for o in opps[:5] if o["trend"]["available"]],
        "score_distribution": [{"range": f"{lo}-{min(hi, 100)}", "count": sum(lo <= g < hi for g in gg)} for lo, hi in BINS],
        "platform_distribution": [{"name": k, "value": v} for k, v in Counter(r["source"] for r in recs).items()],
        "modality_distribution": [{"name": k, "value": v} for k, v in Counter(r["modality"] for r in recs).items()],
        "sentiment_distribution": [{"name": k, "value": v} for k, v in Counter(r["sentiment"] for r in recs).items()],
        "intent_distribution": [{"name": k, "value": v} for k, v in Counter(r["intent"] for r in recs).most_common()],
        "competition_vs_demand": {"available": bool(comp_pts), "points": comp_pts,
                                  "reason": None if comp_pts else "Competition data unavailable - connect the YouTube API to measure content supply."},
        "top_opportunities": [{"id": o["_id"], "topic": o["topic"], "ghostgap": o["scores"]["ghostgap"], "classification": o["scores"]["classification"]}
                              for o in opps[:10]],
    }
