"""Fold-local preprocessing, shared by Draft Probability and Draft Order.

Every transformer here is fitted on TRAINING rows only and rebuilt fresh inside
each fold. Fitting a scaler or an imputer on the full pool would leak the
validation year's distribution backwards into the training years.

Missing-data policy: train-fold median imputation, no missingness indicator
columns, and no complete-case deletion. A missingness indicator is itself a
feature and would carry the outcome — date of birth demonstrated that it would
be the most target-predictive column in the dataset while holding no
basketball information.
"""

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from paths import INTERIM

REFERENCE = INTERIM / "features" / "ncaa_reference_distributions.parquet"

# Metrics the season-relative representation rewrites (DEC-081).
SEASON_RELATIVE_METRICS = [
    "points_per_40", "reb_per_40", "assists_per_40", "steals_per_40",
    "blocks_per_40", "ts_pct", "efg_pct", "three_point_attempt_rate",
    "free_throw_rate", "minutes_per_game",
]

_REFERENCE_CACHE = None


def build_preprocessor(feats, position="ONEHOT", scaling="STANDARD"):
    """ColumnTransformer: median-imputed numeric features + one-hot position_3.

    `position_3` is the ONLY leakage-safe position source (DEC-067). The
    Wikipedia label is outcome-contaminated: it resolves to a five-position
    label for 100% of drafted versus 7.7% of undrafted prospects.
    """
    num_steps = [("impute", SimpleImputer(strategy="median"))]
    if scaling == "STANDARD":
        num_steps.append(("scale", StandardScaler()))
    parts = [("num", Pipeline(num_steps), feats)]
    if position == "ONEHOT":
        parts.append(("pos", OneHotEncoder(handle_unknown="ignore",
                                           sparse_output=False), ["position_3"]))
    return ColumnTransformer(parts, remainder="drop")


def load_reference(path=REFERENCE):
    global _REFERENCE_CACHE
    if _REFERENCE_CACHE is None:
        _REFERENCE_CACHE = pd.read_parquet(path)
    return _REFERENCE_CACHE


def season_relative(df, feats, covered=None):
    """Replace covered metrics by their z-score against the NCAA reference for
    the SAME season and coarse position.

    Leakage-safe on three counts:
      * The reference is the FULL NCAA player population of that season, not the
        prospect sampling frame, and no draft outcome is read to build it.
      * Season Y prospects use season Y references. Those games conclude in
        March/April, before the June draft, so the statistic is available before
        the evaluated draft. No later season is ever consulted.
      * The identical formula is applied to every draft year, train and validate
        alike.
    """
    ref_df = load_reference()
    covered = [c for c in (covered or SEASON_RELATIVE_METRICS) if c in feats]
    out = df.copy()
    ref = ref_df.set_index(["season", "position_3", "metric"])
    for c in covered:
        vals = np.full(len(out), np.nan)
        for (yr, pos), idx in out.groupby(["draft_year", "position_3"]).groups.items():
            key = (int(yr), pos, c)
            if key not in ref.index:
                key = (int(yr), "G", c)
                if key not in ref.index:
                    continue
            mu = float(ref.loc[key, "mean"])
            sd = float(ref.loc[key, "std"])
            if not np.isfinite(sd) or sd <= 0:
                continue
            pos_i = out.index.get_indexer(idx)
            vals[pos_i] = (out.loc[idx, c].to_numpy(dtype="float64") - mu) / sd
        out[c] = vals
    return out
