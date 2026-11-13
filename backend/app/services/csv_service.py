"""CSV parsing, intelligent column detection and validation (no AI involved)."""
import io
from typing import Dict, List, Optional, Tuple

import pandas as pd

ALIASES: Dict[str, List[str]] = {
    "text": ["comment", "text", "body", "content", "message", "review", "feedback", "comment_text", "textdisplay"],
    "timestamp": ["timestamp", "date", "created", "created_at", "created_utc", "time", "published", "publishedat", "datetime"],
    "likes": ["likes", "like_count", "likecount", "upvotes", "score", "engagement", "reactions"],
    "replies": ["replies", "reply_count", "replycount", "num_comments", "comments_count"],
    "platform": ["platform", "source", "channel_type", "network"],
    "author": ["author", "user", "username", "author_name", "authordisplayname"],
    "id": ["id", "comment_id", "commentid"],
}


class CSVError(ValueError):
    """Human-readable CSV problem, safe to show to the user."""


def _read(raw: bytes) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return pd.read_csv(io.BytesIO(raw), encoding=enc, dtype=str, keep_default_na=False, on_bad_lines="skip")
        except UnicodeDecodeError:
            continue
        except (pd.errors.EmptyDataError, pd.errors.ParserError):
            raise CSVError("This file could not be read as a CSV. Check that it is a valid, comma-separated file.")
    raise CSVError("Could not decode this file. Please save it as UTF-8.")


def detect_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    lowered = {c.lower().strip().replace(" ", "_"): c for c in df.columns}
    mapping: Dict[str, Optional[str]] = {}
    for field, names in ALIASES.items():
        mapping[field] = next((lowered[n] for n in names if n in lowered), None)
    if mapping["text"] is None:  # fallback: column with the longest average text
        best, best_len = None, 0.0
        for c in df.columns:
            if c in mapping.values():
                continue
            avg = df[c].astype(str).str.len().mean()
            if avg > best_len and avg >= 15:
                best, best_len = c, avg
        mapping["text"] = best
    return mapping


def _to_int(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0).clip(lower=0).astype(int)


def parse_csv(raw: bytes, default_platform: str = "csv") -> Tuple[List[dict], dict]:
    df = _read(raw)
    if df.empty:
        raise CSVError("The CSV file has no rows.")
    mapping = detect_columns(df)
    if mapping["text"] is None:
        raise CSVError("Could not find a text column. Add a column named 'comment' or 'text'.")

    records, invalid = [], 0
    for i, row in df.iterrows():
        text = str(row[mapping["text"]]).strip()
        if not text:
            invalid += 1
            continue
        g = lambda f: row[mapping[f]] if mapping[f] else None
        records.append({
            "source_id": str(g("id") or i),
            "text": text,
            "timestamp": g("timestamp") or None,
            "likes": int(_to_int(pd.Series([g("likes")]))[0]) if mapping["likes"] else 0,
            "replies": int(_to_int(pd.Series([g("replies")]))[0]) if mapping["replies"] else 0,
            "platform": (str(g("platform")).strip().lower() if mapping["platform"] and g("platform") else default_platform),
            "author": g("author") or None,
            "modality": "text",
        })
    report = {
        "rows_detected": int(len(df)),
        "columns_detected": [str(c) for c in df.columns],
        "column_mapping": mapping,
        "valid_records": len(records),
        "invalid_records": invalid,
        "has_timestamps": mapping["timestamp"] is not None,
        "has_engagement": mapping["likes"] is not None or mapping["replies"] is not None,
    }
    if not records:
        raise CSVError("No usable rows were found - every row had an empty text field.")
    return records, report
