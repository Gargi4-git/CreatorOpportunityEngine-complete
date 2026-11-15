"""AGENT 7 - COMPETITION. Existing-content supply from the YouTube search API for the highest-demand topics.
Never fabricates: without an API key, or on quota/network errors, the affected topics are marked unavailable."""
from app.ml.competition import score_supply
from app.ml.embeddings import get_embedder
from app.services import progress, supply_service, youtube_service

MAX_TOPICS = 8   # search.list costs 100 quota units per call


def run(state: dict) -> dict:
    aid, cids, meta, demand = state["analysis_id"], state["cluster_ids"], state["topic_meta"], state["demand"]
    warnings = list(state.get("warnings", []))
    comp = {c: {"available": False, "reason": "Competition data unavailable"} for c in cids}
    from app.config import settings
    if not settings.youtube_configured:
        progress.step(aid, "competition", "skipped", "Competition data unavailable - YouTube API not connected")
        return {"competition": comp}
    progress.step(aid, "competition", "running")
    embedder = get_embedder(bool(state.get("options", {}).get("multilingual")))
    ranked = sorted(cids, key=lambda c: -(demand[c]["score"] or 0))[:MAX_TOPICS]
    done = 0
    for c in ranked:
        q = meta[c]["search_query"]
        try:
            topic_text = " ".join(x for x in [meta[c]["label"], meta[c].get("audience_need")] if x)
            comp[c] = score_supply(youtube_service.search_supply(q), q, embedder=embedder, topic_text=topic_text,
                                   other=supply_service.collect(q))
            done += 1
        except youtube_service.YouTubeError as exc:
            warnings.append(f"Competition lookup stopped: {exc}")
            for rest in ranked[ranked.index(c):]:
                comp[rest] = {"available": False, "reason": str(exc)}
            break
    progress.step(aid, "competition", "done" if done else "skipped",
                  f"YouTube supply measured for {done}/{len(cids)} topics (top {MAX_TOPICS} by demand)")
    return {"competition": comp, "warnings": warnings}
