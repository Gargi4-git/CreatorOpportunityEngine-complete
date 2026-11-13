"""AGENT 5 - DEMAND. Cluster size, engagement (likes+replies), repeated requests, recency and cross-platform presence
-> Demand 0-100 per topic. Pure statistics - no LLM."""
import numpy as np
import pandas as pd

from app.ml import scoring
from app.ml.sentiment import REQUEST_INTENTS
from app.ml.trends import freshness_scores
from app.services import progress

NON_PLATFORM = {"upload", "csv"}


def run(state: dict) -> dict:
    aid, records, labels, df = state["analysis_id"], state["records"], state["labels"], state["df"]
    cids = state["cluster_ids"]
    progress.step(aid, "demand", "running")
    ts = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    dataset_end = ts.max() if ts.notna().any() else None
    sizes = {c: int((labels == c).sum()) for c in cids}
    eng_tot = {c: int(df.loc[df.cluster_id == c, "engagement"].sum()) for c in cids}
    eng_mean = {c: eng_tot[c] / sizes[c] for c in cids}
    eng_avail = bool((df["engagement"] > 0).any())
    real = df[~df["platform"].isin(NON_PLATFORM)]   # uploads/CSV are not distinct audiences
    n_plat = real["platform"].nunique()
    max_size, max_tot, max_mean = max(sizes.values()), max(eng_tot.values()), max(eng_mean.values())
    demand, fresh = {}, {}
    for c in cids:
        m = df.cluster_id == c
        fr = freshness_scores(df.loc[m, "timestamp"].tolist(), dataset_end)
        fresh[c] = fr
        req = float(np.mean([records[i]["intent"] in REQUEST_INTENTS for i in np.where(labels == c)[0]]))
        plats = real.loc[real.cluster_id == c, "platform"].nunique()
        demand[c] = scoring.demand_score({
            "size": sizes[c] / max_size,
            "engagement": eng_tot[c] / max_tot if eng_avail and max_tot else None,
            "requests": req,
            "recency": fr / 100 if fr is not None else None,
            "cross_platform": (plats - 1) / (n_plat - 1) if n_plat > 1 else None})
    ctx = {"sizes": sizes, "eng_tot": eng_tot, "eng_mean": eng_mean, "eng_avail": eng_avail, "max_mean": max_mean,
           "dataset_end": dataset_end, "n_analyzed": len(records)}
    progress.step(aid, "demand", "done", f"{len(cids)} topics scored")
    return {"demand": demand, "fresh": fresh, "ctx": ctx}
