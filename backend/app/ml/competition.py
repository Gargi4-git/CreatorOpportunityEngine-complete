"""Competition (content supply) score, measured - never guessed.

  YouTube volume   (0.35)  log10(total results)/6   (~1M results, the API's practical ceiling, = 1.0; totalResults is an estimate)
  YouTube recency  (0.20)  share of the top results published in the last 180 days
  Topic coverage   (0.25)  share of the top results whose "title. description" is semantically close to the topic
                           (cosine of embeddings >= threshold) - i.e. videos that actually cover THIS subtopic.
                           Falls back to keyword overlap of titles when no embedder is supplied.
  Other platforms  (0.20)  Stack Overflow (log10(total)/5, blended 70/30 with recency) and Reddit (results sampled/25), averaged
                           over the sources that responded. Omitted (and weights renormalised) when none responded.
Higher score = more existing content = more competition."""
import math
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import numpy as np

STOP = {"the", "a", "an", "to", "of", "for", "and", "in", "on", "with", "how", "is", "my", "your"}
WEIGHTS = {"volume": 0.35, "recency": 0.20, "coverage": 0.25, "other": 0.20}
COVER_THRESHOLD = {"semantic": 0.45, "fallback": 0.15}


def keywords(query: str) -> List[str]:
    return [w for w in re.findall(r"[a-z0-9+#.]+", query.lower()) if w not in STOP and len(w) > 1]


def _coverage(items: List[dict], query: str, embedder=None, topic_text: Optional[str] = None) -> dict:
    if not items:
        return {"share": 0.0, "mean_similarity": None, "method": "none"}
    if embedder is not None and topic_text:
        E = embedder.encode([topic_text] + [f"{i['title']}. {i.get('description', '')[:300]}" for i in items])
        sims = E[1:] @ E[0]
        thr = COVER_THRESHOLD.get(getattr(embedder, "mode", "semantic"), 0.45)
        return {"share": float((sims >= thr).mean()), "mean_similarity": round(float(sims.mean()), 3), "method": "embedding_similarity"}
    terms = keywords(query)
    share = sum(sum(t in i["title"].lower() for t in terms) >= max(1, len(terms) / 2) for i in items) / len(items) if terms else 0.0
    return {"share": float(share), "mean_similarity": None, "method": "keyword_overlap"}


def _other(other: Optional[dict]) -> Optional[dict]:
    parts = {}
    so = (other or {}).get("stackoverflow")
    if so:
        parts["stackoverflow"] = 0.7 * min(1.0, math.log10(1 + so["total"]) / 5) + 0.3 * so["recent_share"]
    rd = (other or {}).get("reddit")
    if rd:
        parts["reddit"] = min(1.0, rd["sample"] / 25) * (0.7 + 0.3 * rd["recent_share"])
    return {"score": sum(parts.values()) / len(parts), "parts": {k: round(v, 3) for k, v in parts.items()}} if parts else None


def score_supply(supply: dict, query: str, now: datetime = None, embedder=None, topic_text: Optional[str] = None,
                 other: Optional[dict] = None) -> dict:
    now = now or datetime.now(timezone.utc)
    items, total = supply["items"], supply["total_results"]
    volume = min(1.0, math.log10(1 + total) / 6)
    cutoff = now - timedelta(days=180)
    dates = [datetime.fromisoformat(i["published_at"].replace("Z", "+00:00")) for i in items]
    recency = (sum(d >= cutoff for d in dates) / len(dates)) if dates else 0.0
    cov = _coverage(items, query, embedder, topic_text)
    oth = _other(other["sources"] if other else None)
    comp = {"volume": volume, "recency": recency, "coverage": cov["share"], "other": oth["score"] if oth else None}
    avail = {k: v for k, v in comp.items() if v is not None}
    score = 100 * sum(WEIGHTS[k] * v for k, v in avail.items()) / sum(WEIGHTS[k] for k in avail)
    return {"available": True, "score": round(score, 1), "query": query, "total_results": total, "sampled": len(items),
            "recent_share": round(recency, 3), "relevance_share": round(cov["share"], 3), "coverage_method": cov["method"],
            "mean_topic_similarity": cov["mean_similarity"],
            "other_platforms": (oth["parts"] if oth else {}), "other_platforms_unavailable": (other or {}).get("unavailable", []),
            "components": {k: round(v, 3) for k, v in avail.items()}}
