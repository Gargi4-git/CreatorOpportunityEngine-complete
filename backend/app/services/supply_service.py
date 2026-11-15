"""Content supply outside YouTube (optional, best-effort): Stack Overflow (public API, no key) and Reddit (needs credentials).
Any failure simply omits that source - the competition score is then computed from the sources that DID answer."""
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from app.config import settings

SE = "https://api.stackexchange.com/2.3/search/advanced"


def stackoverflow(query: str) -> Optional[dict]:
    try:
        base = {"q": query, "site": "stackoverflow", "order": "desc", "sort": "relevance"}
        total = httpx.get(SE, params={**base, "filter": "total"}, timeout=10).json()["total"]
        items = httpx.get(SE, params={**base, "pagesize": 20}, timeout=10).json().get("items", [])
        cutoff = (datetime.now(timezone.utc) - timedelta(days=365)).timestamp()
        recent = (sum(i.get("creation_date", 0) >= cutoff for i in items) / len(items)) if items else 0.0
        return {"total": int(total), "recent_share": round(recent, 3)}
    except Exception:
        return None


def reddit(query: str) -> Optional[dict]:
    if not settings.reddit_configured:
        return None
    try:
        from app.services import reddit_service as rs
        tok = rs._token()
        data = rs._get("/search", tok, {"q": query, "limit": 25, "sort": "relevance", "t": "year", "type": "link"})
        posts = [c["data"] for c in data["data"]["children"]]
        cutoff = (datetime.now(timezone.utc) - timedelta(days=180)).timestamp()
        recent = (sum(p["created_utc"] >= cutoff for p in posts) / len(posts)) if posts else 0.0
        return {"sample": len(posts), "recent_share": round(recent, 3)}
    except Exception:
        return None


def collect(query: str) -> dict:
    out, missing = {}, []
    for name, fn in (("stackoverflow", stackoverflow), ("reddit", reddit)):
        r = fn(query)
        (out.__setitem__(name, r) if r is not None else missing.append(name))
    return {"sources": out, "unavailable": missing}
