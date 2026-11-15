"""Learn GhostGap weights from observed outcomes (closed-loop validation data) with non-negative ridge regression.

outcome ~ intercept + sum_i w_i * component_i      (competition enters as -competition, so a positive weight = a penalty)
Weights are constrained >= 0 and rescaled to the same total magnitude as the default formula (1.0). Because validation data is
small, leave-one-out cross-validated R^2 is reported next to the in-sample fit and the result is flagged as exploratory below
MIN_ROWS_RELIABLE rows."""
from typing import Dict, List

import numpy as np
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge

from app.ml import scoring

NAMES = list(scoring.POSITIVE_WEIGHTS) + list(scoring.NEGATIVE_WEIGHTS)
MIN_ROWS = 5
MIN_ROWS_RELIABLE = 20


def _matrix(rows: List[dict]):
    X = np.array([[np.nan if r["components"].get(n) is None else r["components"][n] / 100 for n in NAMES] for r in rows], dtype=float)
    keep = [j for j in range(len(NAMES)) if not np.isnan(X[:, j]).all()]
    X = X[:, keep]
    means = np.nanmean(X, axis=0)
    idx = np.where(np.isnan(X))
    X[idx] = np.take(means, idx[1])                       # mean-impute partially missing components
    for k, j in enumerate(keep):
        if NAMES[j] in scoring.NEGATIVE_WEIGHTS:
            X[:, k] = -X[:, k]
    return X, [NAMES[j] for j in keep]


def fit(rows: List[dict], alpha: float = 1.0) -> dict:
    """rows: [{components: {...}, outcome: 0-100, default_score: float}]"""
    if len(rows) < MIN_ROWS:
        return {"ok": False, "n": len(rows), "reason": f"Need at least {MIN_ROWS} tracked videos with outcomes (have {len(rows)})."}
    X, used = _matrix(rows)
    y = np.array([r["outcome"] for r in rows], dtype=float) / 100
    if np.ptp(y) == 0:
        return {"ok": False, "n": len(rows), "reason": "All outcomes are identical - nothing to learn from."}
    model = Ridge(alpha=alpha, positive=True).fit(X, y)
    coef = np.maximum(model.coef_, 0)
    if coef.sum() == 0:
        return {"ok": False, "n": len(rows), "reason": "No component showed a positive relationship with the outcome."}
    w = {n: 0.0 for n in NAMES}
    for n, c in zip(used, coef):
        w[n] = round(float(c / coef.sum()), 4)

    # leave-one-out predictions -> honest out-of-sample R^2 / rank correlation
    loo = np.zeros(len(y))
    for i in range(len(y)):
        m = np.ones(len(y), bool); m[i] = False
        loo[i] = Ridge(alpha=alpha, positive=True).fit(X[m], y[m]).predict(X[i:i + 1])[0]
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2_cv = 1 - float(((y - loo) ** 2).sum()) / ss_tot if ss_tot else None
    insample = float(model.score(X, y))
    rho = lambda a, b: None if len(a) < 3 or np.ptp(a) == 0 or np.ptp(b) == 0 else round(float(spearmanr(a, b)[0]), 3)
    learned = [scoring.ghostgap(r["components"], w)["score"] or 0 for r in rows]
    return {"ok": True, "n": len(rows), "weights": w, "default_weights": {**scoring.POSITIVE_WEIGHTS, **scoring.NEGATIVE_WEIGHTS},
            "r2_in_sample": round(insample, 3), "r2_leave_one_out": None if r2_cv is None else round(r2_cv, 3),
            "spearman_default_vs_outcome": rho([r["default_score"] for r in rows], list(y)),
            "spearman_learned_vs_outcome_in_sample": rho(learned, list(y)),
            "reliable": len(rows) >= MIN_ROWS_RELIABLE and (r2_cv or 0) > 0,
            "warning": (None if len(rows) >= MIN_ROWS_RELIABLE and (r2_cv or 0) > 0 else
                        "Exploratory only: too few tracked videos and/or no out-of-sample predictive power (leave-one-out R² ≤ 0). Do not adopt these weights.")}
