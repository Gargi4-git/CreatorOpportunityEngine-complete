"""Competition (content supply) score from REAL YouTube search results.
  volume    (0.5): log10(total results)/6  -> ~1M results (the API's practical ceiling) = 1.0   [totalResults is an estimate]
  recency   (0.3): share of the top results published in the last 180 days
  relevance (0.2): share of top-result titles containing >=50% of the topic's keywords
Higher score = more existing content = more competition."""
import math
import re
from datetime import datetime, timedelta, timezone
from typing import List

STOP = {"the", "a", "an", "to", "of", "for", "and", "in", "on", "with", "how", "is", "my", "your"}


def keywords(query: str) -> List[str]:
    return [w for w in re.findall(r"[a-z0-9+#.]+", query.lower()) if w not in STOP and len(w) > 1]


def score_supply(supply: dict, query: str, now: datetime = None) -> dict:
    now = now or datetime.now(timezone.utc)
    items, total = supply["items"], supply["total_results"]
    terms = keywords(query)
    volume = min(1.0, math.log10(1 + total) / 6)
    cutoff = now - timedelta(days=180)
    dates = [datetime.fromisoformat(i["published_at"].replace("Z", "+00:00")) for i in items]
    recency = (sum(d >= cutoff for d in dates) / len(dates)) if dates else 0.0
    rel = (sum(sum(t in i["title"].lower() for t in terms) >= max(1, len(terms) / 2) for i in items) / len(items)) if items and terms else 0.0
    return {"available": True, "score": round(100 * (0.5 * volume + 0.3 * recency + 0.2 * rel), 1), "query": query,
            "total_results": total, "sampled": len(items), "recent_share": round(recency, 3), "relevance_share": round(rel, 3)}
