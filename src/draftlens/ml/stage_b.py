"""Stage B — how highly a DRAFTED prospect's profile suggests they be selected.

FROZEN as of ML-5 (DEC-086..091). `STAGE_B` below is the selected methodology;
changing it requires a new decision in docs/DECISIONS.md, not a code edit.

    Ridge(alpha=10) | RAW_PICK target | Stage A feature representation

Population: drafted early entrants ONLY. Undrafted prospects are removed, never
given a synthetic pick — see draftlens.ml.datasets.load_stage_b.

Two findings shape how this module may be used:

  THE TARGET BARELY MATTERS. RAW_PICK, PICK_PERCENTILE and DRAFT_VALUE are
  affine images of one another within a draft year, so for a linear model they
  induce the SAME ranking — measured rank correlation 0.998, the residual being
  draft size varying 58-60. Only LOG_PICK is genuinely non-affine, and it is
  worse (DEC-086).

  THE NUMBER IS NOT DISPLAYABLE. MAE is 13.3 picks on a 60-pick draft, 21% of
  predictions land within 5 picks, and the model emits illegal picks (minimum
  -5.1) while collapsing lottery and second-round predictions to within 6 picks
  of each other. Stage B output is an ORDERING; a numeric predicted pick must
  never reach a user (DEC-089).
"""

import json

import numpy as np
from sklearn.pipeline import Pipeline

from draftlens.ml.metrics import strength  # noqa: F401  (canonical orientation)
from draftlens.ml.preprocessing import build_preprocessor, season_relative
from draftlens.ml.validation import assert_no_holdout
from draftlens.paths import CONFIG_ML

CONFIG_PATH = CONFIG_ML / "stage_b.json"

# NOTE ON `normalization`. ML-5 declared it would inherit Stage A's
# SEASON_RELATIVE representation, but the ML-5 experiment imported
# `season_relative` without ever calling it — so every published Stage B number
# (macro Spearman 0.2968, NDCG 0.9043, MAE 13.21 ...) was measured on the
# STANDARD representation. STANDARD is recorded here because it is what the
# evidence actually supports. Switching to SEASON_RELATIVE moves macro Spearman
# to 0.2999 and is therefore a SCIENTIFIC CHANGE requiring its own phase, not a
# refactor. See docs/experiments/ML5_STAGE_B.md, correction notice.
STAGE_B = {
    "family": "Ridge",
    "alpha": 10.0,
    "target": "RAW_PICK",
    "feature_set": "SET_2_BOX_SHOT_PROFILE",
    "normalization": "STANDARD",
    "missing_strategy": "B_TRAIN_MEDIAN",
    "position_handling": "ONEHOT",
    "scaling": "STANDARD",
}

# Tier boundaries chosen on measured density, not tradition (DEC-090). The
# traditional 1-14/15-30/31-45/46-60 scheme leaves 8 of 48 year x tier cells
# below 5 members; this leaves 1 of 36.
TIER_BOUNDS = {"1_lottery": (1, 14), "2_rest_of_r1": (15, 30),
               "3_round_2": (31, 60)}


def load_config(path=CONFIG_PATH):
    return json.loads(path.read_text())


def draft_sizes(cfg=None):
    """Structural draft size per year. NOT a future player outcome.

    Sourced from DATA.md 24.5 with one correction: the documented 2014 value of
    59 is wrong — pick 60 exists in the raw data. Validated against observed
    picks so a future error cannot pass silently.
    """
    cfg = cfg if cfg is not None else load_config()
    return {int(k): int(v) for k, v in cfg["draft_size_by_year"].items()}


# --------------------------------------------------------------- targets
def to_target(pick, size, target):
    """Declared monotonic transformation of the pick. Never fitted."""
    pick = np.asarray(pick, dtype="float64")
    size = np.asarray(size, dtype="float64")
    if target == "RAW_PICK":
        return pick
    if target == "LOG_PICK":
        return np.log(pick)
    if target == "PICK_PERCENTILE":
        return (pick - 1.0) / (size - 1.0)
    if target == "DRAFT_VALUE":
        return (size + 1.0 - pick) / size
    raise ValueError(target)


def to_pick(y, size, target):
    """Exact inverse of `to_target` — brings any prediction back to the pick
    scale so one orientation convention and one MAE definition serve all
    targets."""
    y = np.asarray(y, dtype="float64")
    size = np.asarray(size, dtype="float64")
    if target == "RAW_PICK":
        return y
    if target == "LOG_PICK":
        return np.exp(y)
    if target == "PICK_PERCENTILE":
        return y * (size - 1.0) + 1.0
    if target == "DRAFT_VALUE":
        return size + 1.0 - y * size
    raise ValueError(target)


def tier_of(pick):
    """Fixed development-history boundaries; never refitted per fold."""
    pick = np.asarray(pick)
    out = np.full(len(pick), 2)
    out[pick <= TIER_BOUNDS["2_rest_of_r1"][1]] = 1
    out[pick <= TIER_BOUNDS["1_lottery"][1]] = 0
    return out


# --------------------------------------------------------------- estimator
def build_estimator(family="Ridge", params=None, seed=20260808):
    from sklearn.ensemble import (GradientBoostingRegressor,
                                  HistGradientBoostingRegressor,
                                  RandomForestRegressor)
    from sklearn.linear_model import ElasticNet, Ridge

    p = dict(params or {"alpha": STAGE_B["alpha"]})
    if family == "Ridge":
        return Ridge(random_state=None, **p)
    if family == "ElasticNet":
        return ElasticNet(random_state=seed, max_iter=10000, **p)
    if family == "RandomForestRegressor":
        return RandomForestRegressor(random_state=seed, n_jobs=1, **p)
    if family == "HistGradientBoostingRegressor":
        return HistGradientBoostingRegressor(random_state=seed, **p)
    if family == "GradientBoostingRegressor":
        return GradientBoostingRegressor(random_state=seed, **p)
    raise ValueError(family)


def build_pipeline(feats, family="Ridge", params=None, seed=20260808,
                   estimator=None):
    est = estimator if estimator is not None else build_estimator(family, params, seed)
    return Pipeline([("pre", build_preprocessor(feats)), ("clf", est)])


def prepare(df, feats, normalization=None):
    """Stage B's frozen representation is STANDARD — see the note on STAGE_B."""
    norm = normalization or STAGE_B["normalization"]
    return season_relative(df, feats) if norm == "SEASON_RELATIVE" else df


def fit_predict_fold(train, valid, feats, family="Ridge", params=None,
                     target="RAW_PICK", normalization=None, seed=20260808):
    """Fit on one fold's training years and predict its validation year.

    Returns predicted PICK (not the raw target). The target is z-scored on
    train-fold statistics only so that a single alpha grid means the same amount
    of regularisation on all four target scales; that step is exactly invertible
    and strictly rank-preserving, so nothing reported depends on it.
    """
    train = prepare(assert_no_holdout(train, "stage B train"), feats, normalization)
    valid = prepare(assert_no_holdout(valid, "stage B validate"), feats, normalization)
    y_tr = to_target(train.pick, train.draft_size, target)
    mu, sd = float(np.mean(y_tr)), float(np.std(y_tr))
    sd = sd if sd > 0 else 1.0
    pipe = build_pipeline(feats, family, params, seed)
    pipe.fit(train, (y_tr - mu) / sd)
    y_hat = pipe.predict(valid) * sd + mu
    return to_pick(y_hat, valid.draft_size, target), pipe
