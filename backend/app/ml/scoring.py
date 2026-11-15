"""
Central scoring configuration + GhostGap engine.

The formula lives ONLY here so it can be changed in one place.

GhostGap = 0.30*Demand + 0.20*Trend + 0.20*Pain
         + 0.10*Engagement + 0.10*Freshness - 0.10*Competition

Raw range is [-10, 90]; it is min-max normalised to 0-100 over the *achievable* range.

If a component cannot be measured (no timestamps -> no Trend/Freshness,
no external search -> no Competition, no likes -> no Engagement) it is EXCLUDED
and the achievable range is recomputed over the remaining components.
A missing component is never silently treated as 0 and never invented.
"""
from typing import Dict, Optional

POSITIVE_WEIGHTS = {"demand": 0.30, "trend": 0.20, "pain": 0.20, "engagement": 0.10, "freshness": 0.10}
NEGATIVE_WEIGHTS = {"competition": 0.10}

CLASSIFICATION = [  # (minimum score, label)
    (80, "Critical Opportunity"),
    (60, "High Opportunity"),
    (40, "Moderate Opportunity"),
    (20, "Emerging"),
    (0, "Low Opportunity"),
]

# Demand sub-signal weights (renormalised over the sub-signals that are available)
DEMAND_WEIGHTS = {"size": 0.40, "engagement": 0.20, "requests": 0.20, "recency": 0.10, "cross_platform": 0.10}


def classify(score: float) -> str:
    for minimum, label in CLASSIFICATION:
        if score >= minimum:
            return label
    return "Low Opportunity"


def _clip(x: float) -> float:
    return max(0.0, min(100.0, float(x)))


def demand_score(signals: Dict[str, Optional[float]]) -> dict:
    """signals: size, engagement, requests, recency, cross_platform -> each 0..1, or None if unavailable."""
    avail = {k: v for k, v in signals.items() if v is not None and k in DEMAND_WEIGHTS}
    total_w = sum(DEMAND_WEIGHTS[k] for k in avail)
    if total_w == 0:
        return {"score": None, "components": {}, "unavailable": list(DEMAND_WEIGHTS)}
    score = sum(DEMAND_WEIGHTS[k] * avail[k] for k in avail) / total_w * 100
    return {
        "score": round(_clip(score), 1),
        "components": {k: round(v, 3) for k, v in avail.items()},
        "unavailable": [k for k in DEMAND_WEIGHTS if k not in avail],
    }


def resolve_weights(weights: Optional[Dict[str, float]] = None):
    """Overlay custom weights (non-negative magnitudes; competition is always a penalty) on the central defaults."""
    pos = {k: float((weights or {}).get(k, v)) for k, v in POSITIVE_WEIGHTS.items()}
    neg = {k: float((weights or {}).get(k, v)) for k, v in NEGATIVE_WEIGHTS.items()}
    return pos, neg


def ghostgap(components: Dict[str, Optional[float]], weights: Optional[Dict[str, float]] = None) -> dict:
    """components: demand, trend, pain, engagement, freshness, competition -> 0..100, or None if unavailable.
    weights: optional override {name: magnitude}; defaults are the central POSITIVE/NEGATIVE_WEIGHTS."""
    breakdown, raw, pos_w, neg_w, unavailable = {}, 0.0, 0.0, 0.0, []
    P, N = resolve_weights(weights)

    for name, w in P.items():
        v = components.get(name)
        if v is None:
            unavailable.append(name)
            breakdown[name] = {"score": None, "weight": w, "points": None, "max_points": round(w * 100, 1)}
            continue
        raw += w * v
        pos_w += w
        breakdown[name] = {"score": round(v, 1), "weight": w, "points": round(w * v, 1),
                           "max_points": round(w * 100, 1)}

    for name, w in N.items():
        v = components.get(name)
        if v is None:
            unavailable.append(name)
            breakdown[name] = {"score": None, "weight": -w, "points": None, "max_points": round(w * 100, 1)}
            continue
        raw -= w * v
        neg_w += w
        breakdown[name] = {"score": round(v, 1), "weight": -w, "points": round(-w * v, 1),
                           "max_points": round(w * 100, 1)}

    lo, hi = -neg_w * 100, pos_w * 100
    if hi - lo == 0:
        return {"score": None, "classification": "Insufficient data", "breakdown": breakdown,
                "unavailable": unavailable, "raw": None}
    score = _clip((raw - lo) / (hi - lo) * 100)
    return {"score": round(score, 1), "classification": classify(score), "breakdown": breakdown,
            "unavailable": unavailable, "raw": round(raw, 2)}


QUADRANT_SPLIT = 50  # demand/competition threshold separating high from low


def quadrant(demand: Optional[float], competition: Optional[float]) -> Optional[str]:
    """GhostGap matrix. None when either axis is unavailable (never guessed)."""
    if demand is None or competition is None:
        return None
    hi_d, hi_c = demand >= QUADRANT_SPLIT, competition >= QUADRANT_SPLIT
    return {(True, False): "ghost_gap", (True, True): "saturated", (False, False): "niche", (False, True): "low_value"}[(hi_d, hi_c)]
