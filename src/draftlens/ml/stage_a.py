"""Stage A — P(drafted) for a declared NCAA early entrant.

FROZEN as of ML-4 (DEC-080..085). `STAGE_A` below is the selected methodology;
changing it requires a new decision in docs/DECISIONS.md, not a code edit.

    Logistic regression | SET_2_BOX_SHOT_PROFILE | SEASON_RELATIVE
    | train-fold median imputation | position_3 one-hot
    | class_weight="balanced" | C=0.25 | uncalibrated

Why each part, in one line each:
  * Logistic regression — tree ensembles were rejected: the top random forest
    owed its lead to a single fold with two negative examples and fell from
    rank 1 to rank 12 once that fold was removed (ML4 9).
  * SEASON_RELATIVE — the only change that improved Stage A on evidence,
    improving 11 of 12 measures over the ML-3 incumbent (DEC-081).
  * balanced — costs ~0.001 macro ROC-AUC and improves Brier and ECE
    materially; Stage A's product obligation is a probability (DEC-085).
  * uncalibrated — the fitted model is already the best-calibrated logistic
    model on ECE; every calibration layer costs a training year and compresses
    the usable probability range (DEC-083).
"""

import json

from sklearn.pipeline import Pipeline

from draftlens.leakage import assert_features_safe
from draftlens.ml.preprocessing import build_preprocessor, season_relative
from draftlens.ml.validation import assert_no_holdout
from draftlens.paths import CONFIG_ML

CONFIG_PATH = CONFIG_ML / "stage_a.json"

# The frozen selection. Read by tests as the single source of truth.
STAGE_A = {
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
    """The ML-4 candidate configuration (feature sets, candidates, seed)."""
    return json.loads(path.read_text())


def feature_set(name, fold_cfg=None, cfg=None):
    """Resolve a named Stage A feature set, asserting it carries nothing denied."""
    from draftlens.ml.validation import load_fold_config
    fold_cfg = fold_cfg if fold_cfg is not None else load_fold_config()
    cfg = cfg if cfg is not None else load_config()
    base = list(fold_cfg["feature_sets"]["SET_2_BOX_SHOT_PROFILE"])
    if name == "SET_2R_REDUCED":
        removed = set(cfg["feature_sets"]["SET_2R_REDUCED"]["removed"])
        base = [c for c in base if c not in removed]
    return assert_features_safe(base, name)


def build_estimator(family="LogisticRegression", class_weight="balanced",
                    params=None, seed=20260808):
    """Construct a Stage A classifier. Defaults are the frozen configuration."""
    from sklearn.ensemble import (GradientBoostingClassifier,
                                  HistGradientBoostingClassifier,
                                  RandomForestClassifier)
    from sklearn.linear_model import LogisticRegression

    p = dict(params or {"C": STAGE_A["C"]})
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
    """Fresh Stage A pipeline. Scaling is harmless for trees and keeps the
    preprocessing path identical across families."""
    return Pipeline([("pre", build_preprocessor(feats)),
                     ("clf", build_estimator(family, class_weight, params, seed))])


def prepare(df, feats, normalization=None):
    """Apply the Stage A feature representation to a frame."""
    norm = normalization or STAGE_A["normalization"]
    return season_relative(df, feats) if norm == "SEASON_RELATIVE" else df


def fit_predict_fold(train, valid, feats=None, family=None, class_weight=None,
                     params=None, normalization=None, seed=20260808):
    """Fit on one fold's training years and predict its validation year.

    Both frames pass the holdout guard first: Stage A must never see 2026.
    Returns (probabilities, fitted pipeline).
    """
    from draftlens.ml.validation import load_fold_config
    feats = feats if feats is not None else feature_set(
        STAGE_A["feature_set"], load_fold_config())
    family = family or STAGE_A["family"]
    class_weight = class_weight if class_weight is not None else STAGE_A["class_weight"]
    params = params if params is not None else {"C": STAGE_A["C"]}

    train = prepare(assert_no_holdout(train, "stage A train"), feats, normalization)
    valid = prepare(assert_no_holdout(valid, "stage A validate"), feats, normalization)
    pipe = build_pipeline(feats, family, class_weight, params, seed)
    pipe.fit(train, train.drafted)
    return pipe.predict_proba(valid)[:, 1], pipe
