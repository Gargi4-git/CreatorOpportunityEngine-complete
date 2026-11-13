"""YouTube Data API v3: URL validation, metadata, comments (+replies), and search (for competition analysis)."""
import html
import re
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

import httpx

from app.config import settings

BASE = "https://www.googleapis.com/youtube/v3"
_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


class YouTubeError(RuntimeError):
    """Safe to show to the user."""


class YouTubeNotConfigured(YouTubeError):
    def __init__(self):
        super().__init__("Demo mode / API key required: YOUTUBE_API_KEY is not set, so real comments cannot be fetched.")


def extract_video_id(url: str) -> str:
    u = urlparse((url or "").strip())
    host = (u.hostname or "").lower().removeprefix("www.").removeprefix("m.")
    vid = None
    if host == "youtu.be":
        vid = u.path.lstrip("/").split("/")[0]
    elif host in ("youtube.com", "music.youtube.com"):
        if u.path == "/watch":
            vid = parse_qs(u.query).get("v", [None])[0]
        else:
            m = re.match(r"^/(shorts|embed|live|v)/([^/?]+)", u.path)
            vid = m.group(2) if m else None
        if vid is None and (u.path.startswith(("/@", "/channel/", "/c/", "/user/"))):
            raise YouTubeError("This looks like a channel URL. Please paste a video URL (https://www.youtube.com/watch?v=...).")
    if not vid or not _ID.match(vid):
        raise YouTubeError("Invalid YouTube URL. Use a link like https://www.youtube.com/watch?v=XXXXXXXXXXX.")
    return vid


def _get(path: str, params: dict) -> dict:
    if not settings.youtube_configured:
        raise YouTubeNotConfigured()
    try:
        r = httpx.get(f"{BASE}/{path}", params={**params, "key": settings.youtube_api_key}, timeout=20)
    except httpx.HTTPError:
        raise YouTubeError("Could not reach the YouTube API. Check your network connection.")
    if r.status_code == 200:
        return r.json()
    try:
        reason = r.json()["error"]["errors"][0]["reason"]
    except Exception:
        reason = ""
    if reason in ("quotaExceeded", "rateLimitExceeded", "dailyLimitExceeded"):
        raise YouTubeError("YouTube API quota exceeded. Try again tomorrow or use another API key.")
    if reason == "commentsDisabled":
        raise YouTubeError("Comments are disabled for this video.")
    if reason in ("videoNotFound", "notFound") or r.status_code == 404:
        raise YouTubeError("Video not found - it may be deleted or private.")
    if reason in ("forbidden", "accessNotConfigured") or r.status_code == 403:
        raise YouTubeError("YouTube denied the request. The video may be private, or the API key lacks YouTube Data API v3 access.")
    if r.status_code == 400:
        raise YouTubeError("YouTube rejected the request (bad parameters or invalid API key).")
    raise YouTubeError(f"YouTube API error (HTTP {r.status_code}).")


def fetch_metadata(video_id: str) -> dict:
    items = _get("videos", {"part": "snippet,statistics", "id": video_id}).get("items", [])
    if not items:
        raise YouTubeError("Video not found - it may be deleted or private.")
    it = items[0]
    sn, st = it["snippet"], it.get("statistics", {})
    return {"video_id": video_id, "title": sn.get("title"), "channel": sn.get("channelTitle"),
            "published_at": sn.get("publishedAt"), "view_count": int(st.get("viewCount", 0)),
            "comment_count": int(st.get("commentCount", 0)), "url": f"https://www.youtube.com/watch?v={video_id}"}


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(s or ""))).strip()


def fetch_comments(video_id: str, limit: int = 250) -> List[dict]:
    """Top-level comments plus replies (inline replies; more via comments.list when truncated)."""
    out: List[dict] = []
    token: Optional[str] = None
    while len(out) < limit:
        params = {"part": "snippet,replies", "videoId": video_id, "maxResults": 100, "order": "relevance", "textFormat": "plainText"}
        if token:
            params["pageToken"] = token
        data = _get("commentThreads", params)
        for th in data.get("items", []):
            top = th["snippet"]["topLevelComment"]
            sn = top["snippet"]
            n_replies = int(th["snippet"].get("totalReplyCount", 0))
            out.append(_rec(top["id"], sn, n_replies, video_id))
            replies = th.get("replies", {}).get("comments", [])
            if n_replies > len(replies) and len(out) < limit:
                try:
                    more = _get("comments", {"part": "snippet", "parentId": top["id"], "maxResults": 50, "textFormat": "plainText"})
                    replies = more.get("items", replies)
                except YouTubeError:
                    pass
            for rp in replies:
                out.append(_rec(rp["id"], rp["snippet"], 0, video_id))
            if len(out) >= limit:
                break
        token = data.get("nextPageToken")
        if not token:
            break
    if not out:
        raise YouTubeError("This video has no comments to analyze.")
    return out[:limit]


def _rec(cid: str, sn: dict, replies: int, video_id: str) -> dict:
    return {"source_id": cid, "text": _clean(sn.get("textOriginal") or sn.get("textDisplay")),
            "timestamp": sn.get("publishedAt"), "likes": int(sn.get("likeCount", 0)), "replies": replies,
            "platform": "youtube", "author": sn.get("authorDisplayName"), "modality": "text",
            "url": f"https://www.youtube.com/watch?v={video_id}&lc={cid}"}


def search_supply(query: str, max_results: int = 25) -> dict:
    """Existing-content supply for a topic: estimated total results + the publish dates/titles of the top results."""
    data = _get("search", {"part": "snippet", "q": query, "type": "video", "maxResults": max_results, "order": "relevance"})
    items = [{"title": i["snippet"]["title"], "published_at": i["snippet"]["publishedAt"]} for i in data.get("items", [])]
    return {"total_results": int(data.get("pageInfo", {}).get("totalResults", 0)), "items": items}
