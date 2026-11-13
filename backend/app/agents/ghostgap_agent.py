"""AGENT 8 - GHOSTGAP. Combines Demand, Trend, Pain, Engagement, Freshness and Competition with the central formula
(app/ml/scoring.py) and builds the opportunity objects with a full per-component breakdown."""
import uuid
from collections import Counter

import numpy as np

from app.ml import scoring
from app.services import progress


def run(state: dict) -> dict:
    aid = state["analysis_id"]
    records, E, labels, ctx = state["records"], state["E"], state["labels"], state["ctx"]
    progress.step(aid, "ghostgap", "running")
    opps = []
    for c in state["cluster_ids"]:
        idx = np.where(labels == c)[0]
        centroid = E[idx].mean(axis=0)
        centroid /= (np.linalg.norm(centroid) or 1.0)
        order = idx[np.argsort(-(E[idx] @ centroid))]
        pain = float(np.mean([records[i]["pain_score"] for i in idx]) * 100)
        tr, cp, dm, meta = state["trends"][c], state["competition"][c], state["demand"][c], state["topic_meta"][c]
        gg = scoring.ghostgap({
            "demand": dm["score"], "trend": tr["score"] if tr["available"] else None, "pain": pain,
            "engagement": (ctx["eng_mean"][c] / ctx["max_mean"] * 100) if ctx["eng_avail"] and ctx["max_mean"] else None,
            "freshness": state["fresh"][c], "competition": cp["score"] if cp["available"] else None})
        plat = Counter(records[i]["platform"] for i in idx)
        opps.append({
            "_id": uuid.uuid4().hex, "analysis_id": aid, "cluster_id": c, "topic": meta["label"],
            "topic_label_source": meta["label_source"], "audience_need": meta["audience_need"],
            "search_query": meta["search_query"], "unified_confidence": meta["confidence"], "modality_mix": meta["modality_mix"],
            "evidence_count": len(idx), "share_of_analyzed": round(len(idx) / ctx["n_analyzed"] * 100, 1),
            "scores": {"ghostgap": gg["score"], "classification": gg["classification"], "demand": dm["score"],
                       "trend": tr["score"] if tr["available"] else None, "pain": round(pain, 1),
                       "engagement": gg["breakdown"]["engagement"]["score"], "freshness": gg["breakdown"]["freshness"]["score"],
                       "competition": cp["score"] if cp["available"] else None,
                       "quadrant": scoring.quadrant(dm["score"], cp["score"] if cp["available"] else None)},
            "ghostgap_breakdown": gg["breakdown"], "unavailable_components": gg["unavailable"],
            "demand_detail": dm, "trend": tr, "competition": cp,
            "platform_share": {p: round(n / len(idx) * 100, 1) for p, n in plat.items()},
            "platform_counts": dict(plat),
            "sentiment_distribution": dict(Counter(records[i]["sentiment"] for i in idx)),
            "intent_distribution": dict(Counter(records[i]["intent"] for i in idx)),
            "total_engagement": ctx["eng_tot"][c],
            "member_idx": [int(i) for i in order],          # internal: ordered by closeness to centroid
            "representative_comments": [{"text": records[i]["text"], "likes": records[i]["likes"], "platform": records[i]["platform"],
                                         "modality": records[i].get("modality", "text"), "timestamp": records[i]["timestamp"]}
                                        for i in order[:6]],
            "recommendation": None, "recommendation_status": "pending", "explanation": None, "created_at": progress.now()})
    opps.sort(key=lambda o: (o["scores"]["ghostgap"] is None, -(o["scores"]["ghostgap"] or 0)))
    for r, o in enumerate(opps, 1):
        o["rank"] = r
    progress.step(aid, "ghostgap", "done", f"{len(opps)} opportunities scored")
    return {"opportunities": opps}
