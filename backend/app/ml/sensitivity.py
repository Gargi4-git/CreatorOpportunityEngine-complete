"""Sensitivity analysis of the GhostGap ranking to its weights (Monte-Carlo + one-at-a-time)."""
from typing import Dict, List, Optional

import numpy as np
from scipy.stats import kendalltau

from app.ml import scoring

NAMES = list(scoring.POSITIVE_WEIGHTS) + list(scoring.NEGATIVE_WEIGHTS)


def default_weights() -> Dict[str, float]:
    return {**scoring.POSITIVE_WEIGHTS, **scoring.NEGATIVE_WEIGHTS}


def _ranks(components: List[dict], weights: Dict[str, float]) -> np.ndarray:
    scores = [scoring.ghostgap(c, weights)["score"] for c in components]
    order = sorted(range(len(scores)), key=lambda i: (scores[i] is None, -(scores[i] or 0)))
    r = np.zeros(len(scores), dtype=int)
    for pos, i in enumerate(order, 1):
        r[i] = pos
    return r


def monte_carlo(components: List[dict], base: Dict[str, float], n: int = 500, spread: float = 0.3, seed: int = 7) -> dict:
    """Each draw multiplies every weight by U(1-spread, 1+spread). Reports how stable each topic's rank is."""
    rng = np.random.default_rng(seed)
    base_rank = _ranks(components, base)
    m = len(components)
    ranks = np.zeros((n, m), dtype=int)
    taus = []
    for k in range(n):
        w = {name: base[name] * rng.uniform(1 - spread, 1 + spread) for name in NAMES}
        ranks[k] = _ranks(components, w)
        if m > 2:
            t = kendalltau(base_rank, ranks[k])[0]
            taus.append(0.0 if np.isnan(t) else float(t))
    per = [{"index": i, "p_rank1": round(float((ranks[:, i] == 1).mean()), 3), "p_top3": round(float((ranks[:, i] <= 3).mean()), 3),
            "mean_rank": round(float(ranks[:, i].mean()), 2), "rank_min": int(ranks[:, i].min()), "rank_max": int(ranks[:, i].max()),
            "base_rank": int(base_rank[i])} for i in range(m)]
    top = int(np.argmin(base_rank))
    return {"draws": n, "spread": spread, "per_topic": per, "baseline_top": top, "top1_stability": per[top]["p_rank1"],
            "mean_kendall_tau": round(float(np.mean(taus)), 3) if taus else None,
            "p_any_top1_change": round(float((ranks[:, top] != 1).mean()), 3)}


def one_at_a_time(components: List[dict], base: Dict[str, float], factor: float = 0.5) -> List[dict]:
    """Scale one weight at a time by (1-factor) and (1+factor); report whether the #1 topic changes (tornado data)."""
    base_top = int(np.argmin(_ranks(components, base)))
    out = []
    for name in NAMES:
        row = {"weight": name}
        for tag, mult in (("down", 1 - factor), ("up", 1 + factor)):
            r = _ranks(components, {**base, name: base[name] * mult})
            row[tag] = {"top_index": int(np.argmin(r)), "flipped": int(np.argmin(r)) != base_top,
                        "rank_of_base_top": int(r[base_top])}
        out.append(row)
    return out
