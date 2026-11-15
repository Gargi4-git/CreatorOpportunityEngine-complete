"""Evaluation metrics for the pipeline (feature: Evaluation page). All metrics are computed from real data/labels; nothing is
reported when there is not enough data."""
from typing import Dict, List, Optional

import numpy as np
from scipy.stats import kendalltau, spearmanr
from sklearn.metrics import (accuracy_score, adjusted_rand_score, confusion_matrix, davies_bouldin_score,
                             normalized_mutual_info_score, precision_recall_fscore_support, silhouette_score)

from app.ml import scoring
from app.ml.clustering import cluster_embeddings
from app.ml.sentiment import INTENT_PROTOTYPES, SENTIMENT_PROTOTYPES

INTENTS = list(INTENT_PROTOTYPES)
SENTIMENTS = list(SENTIMENT_PROTOTYPES)
MIN_LABELS = 20


def classification_report(y_true: List[str], y_pred: List[str], labels: List[str]) -> dict:
    present = [l for l in labels if l in set(y_true) | set(y_pred)]
    p, r, f, s = precision_recall_fscore_support(y_true, y_pred, labels=present, zero_division=0)
    majority = max(set(y_true), key=y_true.count)
    return {
        "n": len(y_true), "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "macro_f1": round(float(f.mean()), 4),
        "majority_baseline_accuracy": round(y_true.count(majority) / len(y_true), 4), "majority_class": majority,
        "per_class": [{"label": l, "precision": round(float(p[i]), 3), "recall": round(float(r[i]), 3), "f1": round(float(f[i]), 3), "support": int(s[i])}
                      for i, l in enumerate(present)],
        "confusion": {"labels": present, "matrix": confusion_matrix(y_true, y_pred, labels=present).tolist()},
    }


def clustering_quality(E: np.ndarray, labels: np.ndarray) -> dict:
    n = len(labels)
    mask = labels != -1
    ids = sorted(set(labels.tolist()) - {-1})
    out = {"n_points": int(n), "n_clusters": len(ids), "noise_ratio": round(float((~mask).mean()), 4),
           "cluster_sizes": sorted([int((labels == c).sum()) for c in ids], reverse=True)}
    if len(ids) >= 2 and mask.sum() > len(ids):
        out["silhouette_cosine"] = round(float(silhouette_score(E[mask], labels[mask], metric="cosine")), 4)
        out["davies_bouldin"] = round(float(davies_bouldin_score(E[mask], labels[mask])), 4)
    else:
        out["silhouette_cosine"] = out["davies_bouldin"] = None
        out["note"] = "Need at least 2 clusters to compute silhouette / Davies-Bouldin."
    return out


def agreement(a: np.ndarray, b: np.ndarray) -> dict:
    """Agreement between two clusterings of the same points (noise treated as its own group)."""
    return {"adjusted_rand_index": round(float(adjusted_rand_score(a, b)), 4),
            "normalized_mutual_info": round(float(normalized_mutual_info_score(a, b)), 4)}


def topic_recovery(E: np.ndarray, true_topics: List[str]) -> Optional[dict]:
    """Cluster the labelled texts and compare the result with the hand-labelled topics (ARI / NMI)."""
    if len(set(true_topics)) < 2 or len(true_topics) < 10:
        return None
    pred = cluster_embeddings(E)["labels"]
    return {"n": len(true_topics), "true_topics": len(set(true_topics)), "predicted_clusters": len(set(pred.tolist()) - {-1}),
            "unclustered": int((pred == -1).sum()), **agreement(np.array(true_topics), pred)}


# ------------------------------------------------------------------ GhostGap ablation
def _rank(scores: List[Optional[float]]) -> List[int]:
    order = sorted(range(len(scores)), key=lambda i: (scores[i] is None, -(scores[i] or 0)))
    rank = [0] * len(scores)
    for r, i in enumerate(order, 1):
        rank[i] = r
    return rank


def _compare(full: List[Optional[float]], variant: List[Optional[float]]) -> dict:
    fv = [x if x is not None else -1 for x in full]
    vv = [x if x is not None else -1 for x in variant]
    tau = kendalltau(fv, vv)[0] if len(fv) > 2 else None
    rho = spearmanr(fv, vv)[0] if len(fv) > 2 else None
    top = lambda s, k: set(sorted(range(len(s)), key=lambda i: -(s[i] if s[i] is not None else -1))[:k])
    return {"kendall_tau": None if tau is None or np.isnan(tau) else round(float(tau), 3),
            "spearman": None if rho is None or np.isnan(rho) else round(float(rho), 3),
            "top1_changed": top(full, 1) != top(variant, 1), "top3_overlap": len(top(full, 3) & top(variant, 3))}


def ablation(components: List[Dict[str, Optional[float]]], topics: List[str]) -> dict:
    """Rank topics with the full formula, then (a) drop each component, (b) use each component alone, and report rank stability."""
    names = list(scoring.POSITIVE_WEIGHTS) + list(scoring.NEGATIVE_WEIGHTS)
    full = [scoring.ghostgap(c)["score"] for c in components]
    rows = []
    for n in names:
        measured = any(c.get(n) is not None for c in components)
        if not measured:
            rows.append({"component": n, "measured": False})
            continue
        without = [scoring.ghostgap({**c, n: None})["score"] for c in components]
        alone = [c.get(n) for c in components]
        rows.append({"component": n, "measured": True, "drop": _compare(full, without), "alone": _compare(full, alone),
                     "new_top": topics[int(np.argmax([x if x is not None else -1 for x in without]))]})
    return {"full_top": topics[int(np.argmax([x if x is not None else -1 for x in full]))], "n_topics": len(topics), "components": rows}
