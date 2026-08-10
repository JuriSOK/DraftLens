"""Draft Probability — P(drafted) for a declared NCAA early entrant.

FROZEN. `DRAFT_PROBABILITY` below is the selected methodology; changing it
requires a new decision in docs/METHODOLOGY.md, not a code edit.

    Logistic regression | SET_2_BOX_SHOT_PROFILE | SEASON_RELATIVE
    | train-fold median imputation | position_3 one-hot
    | class_weight="balanced" | C=0.25 | uncalibrated

Why each part, in one line each:
  * Logistic regression — tree ensembles were rejected: the top random forest
    owed its lead to a single fold with two negative examples and fell from
    rank 1 to rank 12 once that fold was removed.
  * SEASON_RELATIVE — the only representation change that improved the model
    on evidence, improving 11 of 12 measures over the prior incumbent.
  * balanced — costs ~0.001 macro ROC-AUC and improves Brier and ECE
    materially; the product obligation here is a probability.
  * uncalibrated — the fitted model is already the best-calibrated logistic
    model on ECE; every calibration layer costs a training year and compresses
    the usable probability range.
"""

import json

import numpy as np
import pandas as pd
from sklearn.metrics import (average_precision_score, brier_score_loss,
                             log_loss, roc_auc_score)
from sklearn.pipeline import Pipeline

from validation import assert_features_safe
from board.preprocessing import build_preprocessor, season_relative
from validation import assert_no_holdout
from paths import CONFIG

CONFIG_PATH = CONFIG / "board.json"

# The frozen selection. Read by tests as the single source of truth.
DRAFT_PROBABILITY = {
    "family": "LogisticRegression",
    "feature_set": "SET_2_BOX_SHOT_PROFILE",
    "normalization": "SEASON_RELATIVE",
    "missing_strategy": "B_TRAIN_MEDIAN",
    "position_handling": "ONEHOT",
    "scaling": "STANDARD",
    "class_weight": "balanced",
    "C": 0.25,
    "calibration": "none",
}


def load_config(path=CONFIG_PATH):
    """The candidate configuration (feature sets, candidates, seed)."""
    return json.loads(path.read_text())


def feature_set(name, fold_cfg=None, cfg=None):
    """Resolve a named feature set, asserting it carries nothing denied."""
    from validation import load_fold_config
    fold_cfg = fold_cfg if fold_cfg is not None else load_fold_config()
    cfg = cfg if cfg is not None else load_config()
    base = list(fold_cfg["feature_sets"]["SET_2_BOX_SHOT_PROFILE"])
    if name == "SET_2R_REDUCED":
        removed = set(cfg["feature_sets"]["SET_2R_REDUCED"]["removed"])
        base = [c for c in base if c not in removed]
    return assert_features_safe(base, name)


def build_estimator(family="LogisticRegression", class_weight="balanced",
                    params=None, seed=20260808):
    """Construct a Draft Probability classifier. Defaults are the frozen configuration."""
    from sklearn.ensemble import (GradientBoostingClassifier,
                                  HistGradientBoostingClassifier,
                                  RandomForestClassifier)
    from sklearn.linear_model import LogisticRegression

    p = dict(params or {"C": DRAFT_PROBABILITY["C"]})
    if family == "LogisticRegression":
        # scikit-learn >= 1.8 expresses the penalty as `l1_ratio`. The configs
        # keep the readable `penalty` name; translate it here. Verified
        # identical: l1_ratio=0.0 reproduces penalty="l2" coefficients exactly,
        # and l1_ratio=1.0 reproduces penalty="l1" sparsity exactly.
        p["l1_ratio"] = {"l2": 0.0, "l1": 1.0}[p.pop("penalty", "l2")]
        return LogisticRegression(max_iter=5000, random_state=seed,
                                  class_weight=class_weight, **p)
    if family == "RandomForest":
        return RandomForestClassifier(random_state=seed, n_jobs=1,
                                      class_weight=class_weight, **p)
    if family == "HistGradientBoosting":
        if class_weight == "balanced":
            return HistGradientBoostingClassifier(random_state=seed,
                                                  class_weight="balanced", **p)
        return HistGradientBoostingClassifier(random_state=seed, **p)
    if family == "GradientBoosting":
        return GradientBoostingClassifier(random_state=seed, **p)
    raise ValueError(family)


def build_pipeline(feats, family="LogisticRegression", class_weight="balanced",
                   params=None, seed=20260808):
    """Fresh pipeline. Scaling is harmless for trees and keeps the
    preprocessing path identical across families."""
    return Pipeline([("pre", build_preprocessor(feats)),
                     ("clf", build_estimator(family, class_weight, params, seed))])


def prepare(df, feats, normalization=None):
    """Apply the feature representation to a frame."""
    norm = normalization or DRAFT_PROBABILITY["normalization"]
    return season_relative(df, feats) if norm == "SEASON_RELATIVE" else df


def fit_predict_fold(train, valid, feats=None, family=None, class_weight=None,
                     params=None, normalization=None, seed=20260808):
    """Fit on one fold's training years and predict its validation year.

    Both frames pass the holdout guard first: the model must never see 2026.
    Returns (probabilities, fitted pipeline).
    """
    from validation import load_fold_config
    feats = feats if feats is not None else feature_set(
        DRAFT_PROBABILITY["feature_set"], load_fold_config())
    family = family or DRAFT_PROBABILITY["family"]
    class_weight = class_weight if class_weight is not None else DRAFT_PROBABILITY["class_weight"]
    params = params if params is not None else {"C": DRAFT_PROBABILITY["C"]}

    train = prepare(assert_no_holdout(train, "draft probability train"), feats, normalization)
    valid = prepare(assert_no_holdout(valid, "draft probability validate"), feats, normalization)
    pipe = build_pipeline(feats, family, class_weight, params, seed)
    pipe.fit(train, train.drafted)
    return pipe.predict_proba(valid)[:, 1], pipe


# ----------------------------------------------------------------- evaluation
def probability_metrics(y, p, low_support_threshold=5):
    """DEGENERATE FOLDS return None, never a flattering default. A validation
    year whose minority class falls below `low_support_threshold` is flagged
    LOW NEGATIVE SUPPORT rather than silently averaged in."""
    y = np.asarray(y).astype(int)
    p = np.clip(np.asarray(p, dtype="float64"), 1e-9, 1 - 1e-9)
    n_pos, n_neg = int(y.sum()), int((y == 0).sum())
    out = dict(n=len(y), drafted=n_pos, undrafted=n_neg,
               base_rate=round(float(y.mean()), 4),
               low_negative_support=bool(min(n_pos, n_neg)
                                         < low_support_threshold))
    both = n_pos > 0 and n_neg > 0
    out["roc_auc"] = round(float(roc_auc_score(y, p)), 4) if both else None
    out["pr_auc"] = round(float(average_precision_score(y, p)), 4) if both else None
    out["log_loss"] = round(float(log_loss(y, p, labels=[0, 1])), 4)
    out["brier"] = round(float(brier_score_loss(y, p)), 4)
    return out


def ranking_metrics(y, p, ks, seed=20260808):
    """Precision@K / Recall@K / NDCG@K on the ranking induced by `p`.

    Ties are broken by a SEEDED random permutation, not by row order — ML-0
    builds the population drafted-first, so a constant predictor that inherited
    row order once scored a spurious NDCG of 1.000.
    """
    y = np.asarray(y).astype(int)
    p = np.asarray(p, dtype="float64")
    rng = np.random.default_rng(seed)
    jitter = rng.permutation(len(p))
    order = np.lexsort((jitter, -p))
    ys = y[order]
    out = {}
    total_pos = int(y.sum())
    for name, k in ks.items():
        k = max(1, min(int(k), len(y)))
        hit = int(ys[:k].sum())
        out[f"precision_at_{name}"] = round(hit / k, 4)
        out[f"recall_at_{name}"] = round(hit / total_pos, 4) if total_pos else None
        disc = 1.0 / np.log2(np.arange(2, k + 2))
        dcg = float((ys[:k] * disc).sum())
        ideal = np.sort(y)[::-1][:k]
        idcg = float((ideal * disc).sum())
        out[f"ndcg_at_{name}"] = round(dcg / idcg, 4) if idcg > 0 else None
        out[f"k_{name}"] = k
    return out


def calibration_bins(y, p, n_bins=10):
    df = pd.DataFrame({"y": np.asarray(y).astype(int),
                       "p": np.asarray(p, dtype="float64")})
    df["bin"] = pd.qcut(df.p, q=n_bins, duplicates="drop", labels=False)
    g = df.groupby("bin").agg(n=("y", "size"), mean_pred=("p", "mean"),
                              observed=("y", "mean")).reset_index()
    g["gap"] = (g.mean_pred - g.observed).round(4)
    return g.round(4)


def expected_calibration_error(y, p):
    """ECE — support-weighted mean |predicted - observed| across the deciles.

    Reported alongside the max gap because a single sparse decile can dominate
    the max while the model is well behaved everywhere else.
    """
    cb = calibration_bins(y, p)
    return round(float((cb.n * cb.gap.abs()).sum() / cb.n.sum()), 4)
