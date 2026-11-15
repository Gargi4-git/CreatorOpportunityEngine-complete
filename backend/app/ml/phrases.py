"""Key-phrase extraction (n-gram counts) shared by the knowledge graph."""
import re
from typing import List, Tuple

from sklearn.feature_extraction.text import CountVectorizer


def key_phrases(texts: List[str], exclude: str = "", k: int = 4, min_count: int = 2) -> List[Tuple[str, int]]:
    if len(texts) < 2:
        return []
    try:
        cv = CountVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1)
        X = cv.fit_transform(texts)
    except ValueError:
        return []
    counts, terms = X.sum(axis=0).A1, cv.get_feature_names_out()
    skip = set(re.findall(r"[a-z0-9]+", exclude.lower()))
    out: List[Tuple[str, int]] = []
    for i in counts.argsort()[::-1]:
        t, n = terms[i], int(counts[i])
        if n < min_count:
            break
        if len(t) < 3 or set(t.split()) <= skip or any(t in o or o in t for o, _ in out):
            continue
        out.append((t, n))
        if len(out) == k:
            break
    return out
