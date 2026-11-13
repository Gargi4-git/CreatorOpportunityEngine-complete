"""Data-quality stage: empty/short filtering, spam, exact duplicates, language, timestamp normalisation.
Near-duplicate removal needs embeddings, so it lives in `drop_near_duplicates` and runs after embedding."""
import html
import re
import unicodedata
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

MIN_CHARS = 8
NEAR_DUP_THRESHOLD = 0.95

_URL = re.compile(r"https?://\S+|www\.\S+", re.I)
_TAGS = re.compile(r"<[^>]+>")
_PROMO = re.compile(
    r"(subscribe to my|check out my (channel|profile|page)|follow me on|dm me|whats?app|telegram|"
    r"giveaway|free (robux|vbucks|gift)|click (the )?link|promo ?code|earn \$?\d+|crypto|forex|"
    r"binary options|sub4sub|visit my)", re.I)


def normalize_text(text) -> str:
    if not isinstance(text, str):
        return ""
    text = html.unescape(text)
    text = _TAGS.sub(" ", text)
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r"\s+", " ", text).strip()


def spam_reason(text: str) -> Optional[str]:
    if len(_URL.findall(text)) >= 2:
        return "multiple_links"
    if _PROMO.search(text):
        return "promotional"
    if re.search(r"(.)\1{9,}", text):
        return "repeated_characters"
    letters = sum(c.isalnum() for c in text)
    if len(text) >= 10 and letters / len(text) < 0.4:
        return "symbol_noise"
    return None


def detect_language(text: str) -> Optional[str]:
    """Return an ISO code only when confident; short text returns None (kept, language unknown)."""
    if len(text) < 25:
        return None
    try:
        from langdetect import DetectorFactory, detect_langs
        DetectorFactory.seed = 0
        top = detect_langs(text)[0]
        return top.lang if top.prob >= 0.9 else None
    except Exception:
        return None


def normalize_timestamp(value) -> Optional[str]:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    ts = pd.to_datetime(value, errors="coerce", utc=True)
    return None if pd.isna(ts) else ts.isoformat()


def clean_records(records: List[dict], english_only: bool = True) -> Tuple[List[dict], dict]:
    """records need at least 'text'. Returns (kept_records, report)."""
    report = {"raw": len(records), "empty_removed": 0, "too_short_removed": 0, "spam_removed": 0,
              "duplicates_removed": 0, "non_english_removed": 0, "near_duplicates_removed": 0}
    kept, seen = [], set()
    for rec in records:
        text = normalize_text(rec.get("text"))
        if not text:
            report["empty_removed"] += 1
            continue
        if len(text) < MIN_CHARS:
            report["too_short_removed"] += 1
            continue
        if spam_reason(text):
            report["spam_removed"] += 1
            continue
        key = re.sub(r"[^a-z0-9 ]", "", text.lower())
        if key in seen:
            report["duplicates_removed"] += 1
            continue
        lang = detect_language(text)
        if english_only and lang is not None and lang != "en":
            report["non_english_removed"] += 1
            continue
        seen.add(key)
        kept.append({**rec, "text": text, "language": lang,
                     "timestamp": normalize_timestamp(rec.get("timestamp"))})
    report["analyzed"] = len(kept)
    return kept, report


def drop_near_duplicates(records: List[dict], embeddings: np.ndarray, threshold: float = NEAR_DUP_THRESHOLD):
    """Greedy: keep highest-engagement record of each near-duplicate group. Embeddings must be L2-normalised."""
    n = len(records)
    if n < 2:
        return records, embeddings, 0
    order = sorted(range(n), key=lambda i: -(records[i].get("likes", 0) + records[i].get("replies", 0)))
    kept_idx: List[int] = []
    kept_mat = np.empty((0, embeddings.shape[1]), dtype=np.float32)
    for i in order:
        if kept_idx and float(np.max(kept_mat @ embeddings[i])) >= threshold:
            continue
        kept_idx.append(i)
        kept_mat = np.vstack([kept_mat, embeddings[i:i + 1]])
    kept_idx.sort()
    return [records[i] for i in kept_idx], embeddings[kept_idx], n - len(kept_idx)
