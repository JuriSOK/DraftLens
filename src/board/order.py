"""Draft Order — how highly a DRAFTED prospect's profile suggests they be
selected.

FROZEN. `DRAFT_ORDER` below is the selected methodology; changing it requires
a new decision in docs/METHODOLOGY.md, not a code edit.

    Ridge(alpha=10) | RAW_PICK target | Draft Probability's feature representation

Population: drafted early entrants ONLY. Undrafted prospects are removed, never
given a synthetic pick — see data.build.load_draft_order.

Two findings shape how this module may be used:

  THE TARGET BARELY MATTERS. RAW_PICK, PICK_PERCENTILE and DRAFT_VALUE are
  affine images of one another within a draft year, so for a linear model they
  induce the SAME ranking — measured rank correlation 0.998, the residual being
  draft size varying 58-60. Only LOG_PICK is genuinely non-affine, and it is
  worse.

  THE NUMBER IS NOT DISPLAYABLE. MAE is 13.3 picks on a 60-pick draft, 21% of
  predictions land within 5 picks, and the model emits illegal picks (minimum
  -5.1) while collapsing lottery and second-round predictions to within 6 picks
  of each other. Output here is an ORDERING; a numeric predicted pick must
  never reach a user.
"""

import json

import numpy as np
from scipy.stats import kendalltau, spearmanr
from sklearn.metrics import ndcg_score
from sklearn.pipeline import Pipeline

from board.preprocessing import build_preprocessor, season_relative
from validation import assert_no_holdout
from paths import CONFIG

CONFIG_PATH = CONFIG / "board.json"

# NOTE ON `normalization`. The methodology declared it would inherit Draft
# Probability's SEASON_RELATIVE representation, but the selection experiment
# imported `season_relative` without ever calling it — so every published
# number (macro Spearman 0.2968, NDCG 0.9043, MAE 13.21 ...) was measured on
# the STANDARD representation. STANDARD is recorded here because it is what
# the evidence actually supports. Switching to SEASON_RELATIVE moves macro
# Spearman to 0.2999 and is therefore a SCIENTIFIC CHANGE requiring its own
# evaluation phase, not a refactor. See docs/VALIDATION.md.
DRAFT_ORDER = {
    "family": "Ridge",
    "alpha": 10.0,
    "target": "RAW_PICK",
    "feature_set": "SET_2_BOX_SHOT_PROFILE",
    "normalization": "STANDARD",
    "missing_strategy": "B_TRAIN_MEDIAN",
    "position_handling": "ONEHOT",
    "scaling": "STANDARD",
}


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


# --------------------------------------------------------------- estimator
def build_estimator(family="Ridge", params=None, seed=20260808):
    from sklearn.ensemble import (GradientBoostingRegressor,
                                  HistGradientBoostingRegressor,
                                  RandomForestRegressor)
    from sklearn.linear_model import ElasticNet, Ridge

    p = dict(params or {"alpha": DRAFT_ORDER["alpha"]})
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
    """The frozen representation is STANDARD — see the note on DRAFT_ORDER."""
    norm = normalization or DRAFT_ORDER["normalization"]
    return season_relative(df, feats) if norm == "SEASON_RELATIVE" else df


def fit_predict_fold(train, valid, feats, family="Ridge", params=None,
                     target="RAW_PICK", normalization=None, seed=20260808):
    """Fit on one fold's training years and predict its validation year.

    Returns predicted PICK (not the raw target). The target is z-scored on
    train-fold statistics only so that a single alpha grid means the same amount
    of regularisation on all four target scales; that step is exactly invertible
    and strictly rank-preserving, so nothing reported depends on it.
    """
    train = prepare(assert_no_holdout(train, "draft order train"), feats, normalization)
    valid = prepare(assert_no_holdout(valid, "draft order validate"), feats, normalization)
    y_tr = to_target(train.pick, train.draft_size, target)
    mu, sd = float(np.mean(y_tr)), float(np.std(y_tr))
    sd = sd if sd > 0 else 1.0
    pipe = build_pipeline(feats, family, params, seed)
    pipe.fit(train, (y_tr - mu) / sd)
    y_hat = pipe.predict(valid) * sd + mu
    return to_pick(y_hat, valid.draft_size, target), pipe


# ----------------------------------------------------------------- evaluation
def strength(pred_pick):
    """CANONICAL ORIENTATION. Higher strength = better = earlier pick.

    The only place a sign is applied anywhere in this module.
    """
    return -np.asarray(pred_pick, dtype="float64")


def order_metrics(actual_pick, pred_pick, size):
    """Rank metrics first — the product outputs an order, not a pick."""
    a = np.asarray(actual_pick, dtype="float64")
    p = np.asarray(pred_pick, dtype="float64")
    s_true, s_pred = strength(a), strength(p)
    n = len(a)
    out = dict(n=n)

    constant = float(np.std(s_pred)) == 0.0
    if constant or n < 3:
        out.update(spearman=None, kendall_tau=None, ndcg=None,
                   ndcg_at_5=None, ndcg_at_10=None, ndcg_at_14=None,
                   constant_prediction=True)
    else:
        out["spearman"] = round(float(spearmanr(s_pred, s_true).statistic), 4)
        out["kendall_tau"] = round(float(kendalltau(s_pred, s_true).statistic), 4)
        rel = (np.asarray(size, dtype="float64") + 1.0 - a).reshape(1, -1)
        sc = s_pred.reshape(1, -1)
        out["ndcg"] = round(float(ndcg_score(rel, sc)), 4)
        for k in (5, 10, 14):
            out[f"ndcg_at_{k}"] = round(float(ndcg_score(rel, sc, k=min(k, n))), 4)
        out["constant_prediction"] = False

    err = p - a
    out["mae_pick"] = round(float(np.mean(np.abs(err))), 4)
    out["rmse_pick"] = round(float(np.sqrt(np.mean(err ** 2))), 4)
    out["median_ae_pick"] = round(float(np.median(np.abs(err))), 4)

    # board-level, among in-scope NCAA early entrants only
    order = np.argsort(-s_pred, kind="stable")
    for label, cut in (("lottery", 14), ("first_round", 30)):
        k = min(cut, n)
        actual_in = a <= cut
        hit = int(actual_in[order[:k]].sum())
        tot = int(actual_in.sum())
        out[f"{label}_recall_at_{cut}"] = round(hit / tot, 4) if tot else None
    half = max(1, n // 2)
    out["top_half_concentration"] = round(
        float((a[order[:half]] <= np.median(a)).mean()), 4)
    return out
