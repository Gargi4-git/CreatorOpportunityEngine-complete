"""Reddit API (app-only OAuth). Accepts a post URL or a subreddit name/URL."""
import re
from datetime import datetime, timezone
from typing import List, Tuple

import httpx

from app.config import settings


class RedditError(RuntimeError):
    """Safe to show to the user."""


class RedditNotConfigured(RedditError):
    def __init__(self):
        super().__init__("Reddit integration unavailable: set REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET and REDDIT_USER_AGENT.")


_POST = re.compile(r"reddit\.com/r/([A-Za-z0-9_]+)/comments/([a-z0-9]+)", re.I)
_SUB_URL = re.compile(r"reddit\.com/r/([A-Za-z0-9_]+)", re.I)
_SUB = re.compile(r"^/?(?:r/)?([A-Za-z0-9_]{2,21})/?$")


def parse_target(value: str) -> Tuple[str, str, str]:
    """-> ('post', subreddit, post_id) or ('subreddit', name, '')"""
    v = (value or "").strip()
    if m := _POST.search(v):
        return "post", m.group(1), m.group(2)
    if m := _SUB_URL.search(v):
        return "subreddit", m.group(1), ""
    if (m := _SUB.match(v)):
        return "subreddit", m.group(1), ""
    raise RedditError("Invalid Reddit input. Use a post URL, a subreddit URL, or a name like r/MachineLearning.")


def _token() -> str:
    if not settings.reddit_configured:
        raise RedditNotConfigured()
    try:
        r = httpx.post("https://www.reddit.com/api/v1/access_token", data={"grant_type": "client_credentials"},
                       auth=(settings.reddit_client_id, settings.reddit_client_secret),
                       headers={"User-Agent": settings.reddit_user_agent}, timeout=15)
    except httpx.HTTPError:
        raise RedditError("Could not reach Reddit. Check your network connection.")
    if r.status_code != 200 or "access_token" not in r.json():
        raise RedditError("Reddit rejected the credentials. Check REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET.")
    return r.json()["access_token"]


def _get(path: str, tok: str, params: dict) -> object:
    try:
        r = httpx.get(f"https://oauth.reddit.com{path}", params={**params, "raw_json": 1},
                      headers={"Authorization": f"bearer {tok}", "User-Agent": settings.reddit_user_agent}, timeout=20)
    except httpx.HTTPError:
        raise RedditError("Could not reach Reddit. Check your network connection.")
    if r.status_code == 429:
        raise RedditError("Reddit rate limit reached. Please wait a minute and try again.")
    if r.status_code in (403, 404):
        raise RedditError("Reddit content not found or private.")
    if r.status_code != 200:
        raise RedditError(f"Reddit API error (HTTP {r.status_code}).")
    return r.json()


def _iso(utc: float) -> str:
    return datetime.fromtimestamp(utc, tz=timezone.utc).isoformat()


def _post_rec(d: dict) -> dict:
    text = (d.get("title", "") + ". " + (d.get("selftext") or "")).strip()
    return {"source_id": d["id"], "text": text, "timestamp": _iso(d["created_utc"]), "likes": int(d.get("score", 0)),
            "replies": int(d.get("num_comments", 0)), "platform": "reddit", "author": d.get("author"), "modality": "text",
            "subreddit": d.get("subreddit"), "url": "https://reddit.com" + d.get("permalink", "")}


def _flatten(children: list, out: list, sub: str):
    for c in children:
        if c.get("kind") != "t1":
            continue
        d = c["data"]
        if d.get("body") and d["body"] not in ("[deleted]", "[removed]"):
            out.append({"source_id": d["id"], "text": d["body"], "timestamp": _iso(d["created_utc"]), "likes": int(d.get("score", 0)),
                        "replies": 0, "platform": "reddit", "author": d.get("author"), "modality": "text", "subreddit": sub,
                        "url": "https://reddit.com" + d.get("permalink", "")})
        rep = d.get("replies")
        if isinstance(rep, dict):
            _flatten(rep["data"]["children"], out, sub)


def fetch(target: str, limit: int = 100) -> Tuple[List[dict], dict]:
    kind, sub, pid = parse_target(target)
    tok = _token()
    records: List[dict] = []
    if kind == "post":
        data = _get(f"/r/{sub}/comments/{pid}", tok, {"limit": limit, "sort": "top"})
        records.append(_post_rec(data[0]["data"]["children"][0]["data"]))
        _flatten(data[1]["data"]["children"], records, sub)
    else:
        posts = _get(f"/r/{sub}/hot", tok, {"limit": min(limit, 50)})["data"]["children"]
        posts = [p["data"] for p in posts if not p["data"].get("stickied")]
        records += [_post_rec(p) for p in posts]
        for p in sorted(posts, key=lambda d: -d.get("num_comments", 0))[:5]:   # comments from the 5 busiest threads
            if len(records) >= limit:
                break
            data = _get(f"/r/{sub}/comments/{p['id']}", tok, {"limit": 50, "sort": "top"})
            _flatten(data[1]["data"]["children"], records, sub)
    records = records[:limit]
    if not records:
        raise RedditError("No posts or comments were found.")
    return records, {"kind": kind, "subreddit": sub, "post_id": pid or None}
