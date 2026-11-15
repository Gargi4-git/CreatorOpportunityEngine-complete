"""Semantic clustering: HDBSCAN on embeddings, with a silhouette-selected KMeans fallback; keyword topic labels."""
from typing import List

import numpy as np
from sklearn.cluster import HDBSCAN, KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import silhouette_score


def cluster_embeddings(E: np.ndarray) -> dict:
    n = len(E)
    if n < 4:
        return {"labels": np.zeros(n, dtype=int), "method": "single_group", "n_clusters": 1 if n else 0}
    mcs = max(3, int(round(n * 0.03)))
    labels = HDBSCAN(min_cluster_size=mcs, min_samples=2, metric="euclidean", copy=True).fit_predict(E)  # unit vectors -> cosine-equivalent
    method = "hdbscan"
    if len(set(labels) - {-1}) == 0:
        best_k, best = None, -1.0
        for k in range(2, min(8, n // 2) + 1):
            cand = KMeans(n_clusters=k, n_init=10, random_state=42).fit_predict(E)
            if len(set(cand)) < 2:
                continue
            s = silhouette_score(E, cand)
            if s > best:
                best_k, best, labels = k, s, cand
        method = "kmeans_silhouette_fallback"
        if best_k is None:
            labels = np.zeros(n, dtype=int)
            method = "single_group"
    return {"labels": np.asarray(labels), "method": method, "n_clusters": len(set(labels) - {-1})}


def label_clusters(texts: List[str], labels: np.ndarray, multilingual: bool = False) -> dict:
    """Deterministic keyword label per cluster using TF-IDF over cluster-documents (class-based TF-IDF)."""
    ids = sorted(set(int(l) for l in labels) - {-1})
    if not ids:
        return {}
    docs = [" ".join(t for t, l in zip(texts, labels) if l == i) for i in ids]
    vec = TfidfVectorizer(stop_words=None if multilingual else "english", ngram_range=(1, 2), min_df=1, sublinear_tf=True)
    X = vec.fit_transform(docs)
    terms = np.array(vec.get_feature_names_out())
    out = {}
    for row, cid in enumerate(ids):
        scores = X[row].toarray().ravel()
        picked: List[str] = []
        for j in scores.argsort()[::-1]:
            term = terms[j]
            if scores[j] <= 0:
                break
            if any(term in p or p in term for p in picked):
                continue
            picked.append(term)
            if len(picked) == 3:
                break
        out[cid] = " / ".join(p.title() for p in picked) if picked else f"Topic {cid}"
    return out
