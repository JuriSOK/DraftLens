"""Transparent baselines a fitted model must beat.

ML_SPEC 15: complex models must beat simple ones on temporal validation before
being considered. Public mock drafts and analyst consensus boards are PROHIBITED
as baselines in the predictive pipeline (DEC-013) — they may only ever appear as
external comparison benchmarks.

Every reference distribution here is computed on the TRAINING fold only.
"""

import numpy as np
import pandas as pd

from draftlens.ml.metrics import to_unit

COMPOSITE_COLS = ["points_per_40", "reb_per_40", "assists_per_40",
                  "steals_per_40", "blocks_per_40", "ts_pct"]


# ----------------------------------------------------- Stage A (ML_SPEC 15)
def b0_prevalence(train, valid, **_):
    """Training-fold prevalence for every validation prospect."""
    p = float(train.drafted.mean())
    return np.full(len(valid), p)


def _train_z(train, valid, cols):
    mu, sd = train[cols].mean(), train[cols].std(ddof=0).replace(0, np.nan)
    return ((train[cols] - mu) / sd), ((valid[cols] - mu) / sd)


def b1_scoring_only(train, valid, **_):
    """ML_SPEC #1 — scoring average only. Rank-mapped to [0,1] for metrics."""
    tr, va = _train_z(train, valid, ["points_per_40"])
    s = va["points_per_40"].fillna(tr["points_per_40"].median())
    return to_unit(s.to_numpy())


def b2_standardised_composite(train, valid, **_):
    """ML_SPEC #2 — equal-weight z-score composite. z fitted on TRAIN only.
    HEURISTIC baseline, explicitly not a DraftLens score."""
    trz, vaz = _train_z(train, valid, COMPOSITE_COLS)
    med = trz.median()
    score = vaz.fillna(med).mean(axis=1)
    return to_unit(score.to_numpy())


def b4_position_percentile_composite(train, valid, **_):
    """ML_SPEC #4 — equal-weight composite of WITHIN-POSITION percentile ranks.
    Percentile reference distributions come from the training fold only.

    The standing Stage A ranking benchmark (DEC-079): macro ROC-AUC 0.6943,
    macro NDCG@drafted 0.7171, still un-beaten on NDCG after ML-4.
    """
    parts = []
    for c in COMPOSITE_COLS:
        vals = np.full(len(valid), np.nan)
        for pos in valid.position_3.unique():
            ref = train.loc[train.position_3 == pos, c].dropna().to_numpy()
            if ref.size < 10:
                ref = train[c].dropna().to_numpy()
            m = (valid.position_3 == pos).to_numpy()
            v = valid.loc[m, c].to_numpy(dtype="float64")
            pct = np.array([np.nan if np.isnan(x)
                            else (ref < x).mean() for x in v])
            vals[m] = pct
        parts.append(pd.Series(vals, index=valid.index))
    comp = pd.concat(parts, axis=1)
    return to_unit(comp.fillna(0.5).mean(axis=1).to_numpy())


# ------------------------------------------------------- Stage B (ML5 §7)
def b5a_global_mean_pick(train, valid, **_):
    """Numeric-error reference only. Constant, so its ranking is undefined and
    `stage_b_metrics` reports null rank metrics for it rather than 1.0."""
    return np.full(len(valid), float(train.pick.mean()))


def b5b_position_mean_pick(train, valid, **_):
    """Historical mean pick by leakage-safe position_3, training history only.

    Measured NEGATIVE (macro Spearman -0.1235): coarse position does not merely
    fail to predict pick, it predicts it backwards.
    """
    g = train.groupby("position_3").pick.mean()
    glob = float(train.pick.mean())
    return valid.position_3.map(g).fillna(glob).to_numpy(dtype="float64")


def b5c_percentile_composite(train, valid, **_):
    """B4-style within-position percentile composite, mapped onto the pick scale
    so it shares the Stage B metric path: a HIGH composite means an EARLY pick."""
    parts = []
    for c in COMPOSITE_COLS:
        vals = np.full(len(valid), np.nan)
        for pos in valid.position_3.unique():
            ref = train.loc[train.position_3 == pos, c].dropna().to_numpy()
            if ref.size < 10:
                ref = train[c].dropna().to_numpy()
            m = (valid.position_3 == pos).to_numpy()
            v = valid.loc[m, c].to_numpy(dtype="float64")
            vals[m] = [np.nan if np.isnan(x) else (ref < x).mean() for x in v]
        parts.append(pd.Series(vals, index=valid.index))
    comp = pd.concat(parts, axis=1).fillna(0.5).mean(axis=1).to_numpy()
    lo, hi = float(train.pick.min()), float(train.pick.max())
    return hi - comp * (hi - lo)


STAGE_B_BASELINES = {"B5A_GLOBAL_MEAN_PICK": b5a_global_mean_pick,
                     "B5B_POSITION_MEAN_PICK": b5b_position_mean_pick,
                     "B5C_PERCENTILE_COMPOSITE": b5c_percentile_composite}
