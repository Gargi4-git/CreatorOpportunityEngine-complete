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
    return {"video_id": video_id, "title": sn.get("title"), "channel": sn.get("channelTitle"), "channel_id": sn.get("channelId"),
            "published_at": sn.get("publishedAt"), "view_count": int(st.get("viewCount", 0)),
            "comment_count": int(st.get("commentCount", 0)), "url": f"https://www.youtube.com/watch?v={video_id}"}


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(s or ""))).strip()


def fetch_comments(video_id: str, limit: int = 250, video_title: str = None) -> List[dict]:
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
            out.append(_rec(top["id"], sn, n_replies, video_id, video_title))
            replies = th.get("replies", {}).get("comments", [])
            if n_replies > len(replies) and len(out) < limit:
                try:
                    more = _get("comments", {"part": "snippet", "parentId": top["id"], "maxResults": 50, "textFormat": "plainText"})
                    replies = more.get("items", replies)
                except YouTubeError:
                    pass
            for rp in replies:
                out.append(_rec(rp["id"], rp["snippet"], 0, video_id, video_title))
            if len(out) >= limit:
                break
        token = data.get("nextPageToken")
        if not token:
            break
    if not out:
        raise YouTubeError("This video has no comments to analyze.")
    return out[:limit]


def _rec(cid: str, sn: dict, replies: int, video_id: str, video_title: str = None) -> dict:
    return {"video_id": video_id, "video_title": video_title, "source_id": cid, "text": _clean(sn.get("textOriginal") or sn.get("textDisplay")),
            "timestamp": sn.get("publishedAt"), "likes": int(sn.get("likeCount", 0)), "replies": replies,
            "platform": "youtube", "author": sn.get("authorDisplayName"), "modality": "text",
            "url": f"https://www.youtube.com/watch?v={video_id}&lc={cid}"}


def search_supply(query: str, max_results: int = 25) -> dict:
    """Existing-content supply for a topic: estimated total results + the publish dates/titles of the top results."""
    data = _get("search", {"part": "snippet", "q": query, "type": "video", "maxResults": max_results, "order": "relevance"})
    items = [{"title": i["snippet"]["title"], "description": i["snippet"].get("description", ""), "published_at": i["snippet"]["publishedAt"]}
             for i in data.get("items", [])]
    return {"total_results": int(data.get("pageInfo", {}).get("totalResults", 0)), "items": items}


# ------------------------------------------------------------------ channel-level analysis
_CHANNEL_ID = re.compile(r"^UC[A-Za-z0-9_-]{22}$")


def parse_channel_url(url: str) -> Tuple[str, str]:
    """-> (kind, value) with kind in handle | id | user | custom."""
    u = urlparse((url or "").strip())
    host = (u.hostname or "").lower().removeprefix("www.").removeprefix("m.")
    if host != "youtube.com":
        raise YouTubeError("Invalid channel URL. Use a link like https://www.youtube.com/@channelname")
    parts = [p for p in u.path.split("/") if p]
    if parts and parts[0].startswith("@"):
        return "handle", parts[0]
    if len(parts) >= 2 and parts[0] == "channel" and _CHANNEL_ID.match(parts[1]):
        return "id", parts[1]
    if len(parts) >= 2 and parts[0] == "user":
        return "user", parts[1]
    if len(parts) >= 2 and parts[0] == "c":
        return "custom", parts[1]
    raise YouTubeError("Invalid channel URL. Use https://www.youtube.com/@name or https://www.youtube.com/channel/UC...")


def resolve_channel(url: str) -> dict:
    kind, value = parse_channel_url(url)
    params = {"part": "snippet,contentDetails,statistics"}
    if kind == "custom":      # legacy /c/ URLs have no direct lookup: search (100 quota units)
        hit = _get("search", {"part": "snippet", "q": value, "type": "channel", "maxResults": 1}).get("items", [])
        if not hit:
            raise YouTubeError("Channel not found.")
        kind, value = "id", hit[0]["snippet"]["channelId"]
    params[{"handle": "forHandle", "id": "id", "user": "forUsername"}[kind]] = value
    items = _get("channels", params).get("items", [])
    if not items:
        raise YouTubeError("Channel not found.")
    it = items[0]
    return {"channel_id": it["id"], "title": it["snippet"]["title"], "subscribers": int(it.get("statistics", {}).get("subscriberCount", 0)),
            "uploads_playlist": it["contentDetails"]["relatedPlaylists"]["uploads"]}


def recent_videos(uploads_playlist: str, n: int) -> List[dict]:
    data = _get("playlistItems", {"part": "snippet,contentDetails", "playlistId": uploads_playlist, "maxResults": min(max(n, 1), 50)})
    return [{"video_id": i["contentDetails"]["videoId"], "title": i["snippet"]["title"],
             "published_at": i["contentDetails"].get("videoPublishedAt") or i["snippet"].get("publishedAt")} for i in data.get("items", [])][:n]


def fetch_channel_comments(videos: List[dict], per_video: int) -> Tuple[List[dict], List[dict]]:
    """Comments of each recent video. Videos with disabled comments are skipped (and reported), not fatal."""
    records, report = [], []
    for v in videos:
        try:
            recs = fetch_comments(v["video_id"], per_video, v["title"])
            records += recs
            report.append({**v, "comments": len(recs)})
        except YouTubeError as exc:
            if "quota" in str(exc).lower():
                raise
            report.append({**v, "comments": 0, "skipped": str(exc)})
    if not records:
        raise YouTubeError("None of the channel's recent videos has comments to analyze.")
    return records, report


def video_stats(video_ids: List[str]) -> dict:
    """views / likes / comment count / publish date / channel for up to 50 videos (1 quota unit)."""
    out = {}
    for i in range(0, len(video_ids), 50):
        data = _get("videos", {"part": "snippet,statistics", "id": ",".join(video_ids[i:i + 50])})
        for it in data.get("items", []):
            st = it.get("statistics", {})
            out[it["id"]] = {"title": it["snippet"]["title"], "channel_id": it["snippet"].get("channelId"), "published_at": it["snippet"].get("publishedAt"),
                             "views": int(st.get("viewCount", 0)), "likes": int(st.get("likeCount", 0)), "comments": int(st.get("commentCount", 0))}
    return out


def _age_days(published_at: Optional[str]) -> float:
    if not published_at:
        return 1.0
    d = datetime.now(timezone.utc) - datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    return max(1.0, d.total_seconds() / 86400)


def views_per_day(stats: dict) -> float:
    return stats["views"] / _age_days(stats.get("published_at"))


def channel_baseline_rate(channel_id: str, exclude_video: str, n: int = 10) -> Optional[float]:
    """Median views/day of the channel's most recent OTHER videos: the creator's own baseline for 'did this video outperform?'."""
    ch = _get("channels", {"part": "contentDetails", "id": channel_id}).get("items", [])
    if not ch:
        return None
    vids = [v["video_id"] for v in recent_videos(ch[0]["contentDetails"]["relatedPlaylists"]["uploads"], n + 1) if v["video_id"] != exclude_video][:n]
    rates = sorted(views_per_day(s) for s in video_stats(vids).values())
    if not rates:
        return None
    mid = len(rates) // 2
    return float(rates[mid] if len(rates) % 2 else (rates[mid - 1] + rates[mid]) / 2)
