"""AGENT 6 - TREND. Mentions-over-time per topic from real timestamps (Pandas). Unavailable (not invented) without them."""
from app.ml.trends import trend_for
from app.services import progress


def run(state: dict) -> dict:
    aid, df = state["analysis_id"], state["df"]
    progress.step(aid, "trend", "running")
    all_ts = df["timestamp"].tolist()
    trends = {c: trend_for(all_ts, df.loc[df.cluster_id == c, "timestamp"].tolist()) for c in state["cluster_ids"]}
    n = sum(t["available"] for t in trends.values())
    progress.step(aid, "trend", "done" if n else "skipped",
                  f"{n}/{len(trends)} topics have enough timestamped data" if n else "Trend unavailable - timestamps required")
    return {"trends": trends}
