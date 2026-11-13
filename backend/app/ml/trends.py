"""Trend analytics from REAL timestamps only. Returns available=False instead of inventing a number."""
import math
from typing import List, Optional

import pandas as pd

MIN_TIMESTAMPED = 6
MIN_BUCKETS = 3


def choose_granularity(ts: pd.Series) -> Optional[str]:
    span = (ts.max() - ts.min()).days
    if span >= 90:
        return "M"
    if span >= 14:
        return "W"
    if span >= 3:
        return "D"
    return None


def trend_for(all_ts: List[Optional[str]], topic_ts: List[Optional[str]]) -> dict:
    """Bucket the topic's mentions on the dataset-wide timeline, compare late vs early half."""
    ts_all = pd.to_datetime(pd.Series([t for t in all_ts if t]), utc=True, errors="coerce").dropna()
    ts_topic = pd.to_datetime(pd.Series([t for t in topic_ts if t]), utc=True, errors="coerce").dropna()
    if len(ts_all) < MIN_TIMESTAMPED or len(ts_topic) < 2:
        return {"available": False, "reason": "Trend unavailable - timestamps required"}
    gran = choose_granularity(ts_all)
    if gran is None:
        return {"available": False, "reason": "Trend unavailable - timestamps span fewer than 3 days"}
    # tz-naive for period conversion
    all_p = ts_all.dt.tz_localize(None).dt.to_period(gran)
    topic_p = ts_topic.dt.tz_localize(None).dt.to_period(gran)
    periods = pd.period_range(all_p.min(), all_p.max(), freq=gran)
    if len(periods) < MIN_BUCKETS:
        return {"available": False, "reason": "Trend unavailable - need at least 3 time periods"}
    counts = topic_p.value_counts().reindex(periods, fill_value=0).sort_index()
    series = [{"period": str(p), "mentions": int(c)} for p, c in counts.items()]
    half = len(counts) // 2
    early, late = counts.iloc[:half].mean(), counts.iloc[len(counts) - half:].mean()
    growth_ratio = (late - early) / max(early, 1.0)
    return {
        "available": True,
        "granularity": {"M": "month", "W": "week", "D": "day"}[gran],
        "series": series,
        "early_mean": round(float(early), 2),
        "late_mean": round(float(late), 2),
        "growth_percent": round(float(growth_ratio * 100), 1),
        "low_baseline": bool(early < 1),
        "score": round(50 + 50 * math.tanh(growth_ratio), 1),  # 0 growth -> 50, doubling -> ~88, collapse -> ~12
    }


def freshness_scores(timestamps: List[Optional[str]], dataset_end: Optional[pd.Timestamp], half_life_days: float = 30.0):
    """Mean exponential recency (0-100) relative to the newest record in the dataset. None if no timestamps."""
    ts = pd.to_datetime(pd.Series([t for t in timestamps if t]), utc=True, errors="coerce").dropna()
    if ts.empty or dataset_end is None:
        return None
    age = (dataset_end - ts).dt.total_seconds() / 86400
    return float((0.5 ** (age / half_life_days)).mean() * 100)
