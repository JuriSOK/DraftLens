"""ML-3 shared helpers: folds, feature sets, baselines, metrics.

Deliberately small — no ML framework. Every transformer is fitted inside a fold
on training years only. 2026 is never loadable from here.
"""

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, brier_score_loss,
                             log_loss, roc_auc_score)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_model_dataset import OUT as ML0  # noqa: E402
from build_ml2_features import OUT as ML2  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "ml3_baselines.json"
OUT = ROOT / "data" / "interim" / "ml3"
HOLDOUT_YEAR = 2026

# Never permitted in X.
DENIED = {"drafted", "pick", "round", "drafting_team", "early_entrant",
          "population_source", "position_from_population",
          "class_from_population", "match_method", "match_confidence",
          "date_of_birth", "age", "current_age", "dob",
          "canonical_prospect_id", "player_name", "normalized_name",
          "college", "wikipedia_title", "hoopr_athlete_id", "draft_year",
          "shot_fga_coverage_ratio", "n_teams", "experience_years"}
DENIED_SUBSTR = ("jump_shot", "nba_", "mock", "consensus", "analyst")


def load_config():
    return json.loads(CONFIG_PATH.read_text())


def load_development():
    """ML-2 features joined to development targets. 2026 can never appear."""
    f = pd.read_parquet(ML2 / "features_2014_2025.parquet")
    t = pd.read_parquet(ML0 / "targets_2014_2025.parquet")
    m = f.merge(t[["canonical_prospect_id", "drafted", "pick"]],
                on="canonical_prospect_id", how="inner")
    assert HOLDOUT_YEAR not in set(m.draft_year), "HOLDOUT GUARD: 2026 present"
    return m


def load_robustness():
    f = pd.read_parquet(ML2 / "features_2011_2013.parquet")
    t = pd.read_parquet(ML0 / "targets_2011_2013.parquet")
    m = f.merge(t[["canonical_prospect_id", "drafted", "pick"]],
                on="canonical_prospect_id", how="inner")
    assert HOLDOUT_YEAR not in set(m.draft_year)
    return m


def assert_no_holdout(df, where=""):
    if HOLDOUT_YEAR in set(pd.Series(df["draft_year"]).unique()):
        raise AssertionError(f"HOLDOUT GUARD: 2026 reached {where}")
    return df


def folds(cfg):
    """(train_years, validate_year) tuples. Train is always strictly earlier."""
    out = []
    for f in cfg["folds"]:
        lo, hi = f["train"]
        vy = f["validate"]
        tr = list(range(lo, hi + 1))
        assert max(tr) < vy, "training years must precede the validation year"
        assert vy != HOLDOUT_YEAR and HOLDOUT_YEAR not in tr
        out.append((f["fold"], tr, vy))
    return out


# ------------------------------------------------------------- feature sets
def resolve_features(cfg, name, train_df, strategy):
    """Feature list for a set + missing strategy, decided on TRAINING data only."""
    feats = list(cfg["feature_sets"][name])
    sparse = set(cfg["sparse_ratio_features"])
    if strategy == "A_CONSERVATIVE_EXCLUSION":
        feats = [c for c in feats if c not in sparse]
    elif strategy == "C_HIGH_COVERAGE":
        feats = [c for c in feats if train_df[c].notna().mean() >= 0.97]
    bad = [c for c in feats if c in DENIED
           or any(s in c.lower() for s in DENIED_SUBSTR)]
    if bad:
        raise AssertionError(f"denied features in {name}: {bad}")
    return feats


def make_pipeline(feats, strategy, position, scaling, class_weight, C, seed):
    """Fresh sklearn Pipeline — refitted inside every fold, never reused."""
    num_steps = [("impute", SimpleImputer(strategy="median"))]
    if scaling == "STANDARD":
        num_steps.append(("scale", StandardScaler()))
    num = Pipeline(num_steps)
    parts = [("num", num, feats)]
    if position == "ONEHOT":
        parts.append(("pos", OneHotEncoder(handle_unknown="ignore",
                                           sparse_output=False), ["position_3"]))
    pre = ColumnTransformer(parts, remainder="drop")
    clf = LogisticRegression(C=C, class_weight=class_weight, max_iter=5000,
                             solver="lbfgs", random_state=seed)
    return Pipeline([("pre", pre), ("clf", clf)])


def position_median_impute(train, valid, feats):
    """Train-fold medians computed within position_3; global train median as
    fallback. Validation values never influence a fill value."""
    tr, va = train.copy(), valid.copy()
    gmed = tr[feats].median()
    pmed = tr.groupby("position_3")[feats].median()
    for df in (tr, va):
        for pos in df.position_3.dropna().unique():
            mask = df.position_3 == pos
            fill = pmed.loc[pos] if pos in pmed.index else gmed
            df.loc[mask, feats] = df.loc[mask, feats].fillna(fill)
        df[feats] = df[feats].fillna(gmed)
    return tr, va


# ---------------------------------------------------------------- baselines
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
    return _to_unit(s.to_numpy())


COMPOSITE_COLS = ["points_per_40", "reb_per_40", "assists_per_40",
                  "steals_per_40", "blocks_per_40", "ts_pct"]


def b2_standardised_composite(train, valid, **_):
    """ML_SPEC #2 — equal-weight z-score composite. z fitted on TRAIN only.
    HEURISTIC baseline, explicitly not a DraftLens score."""
    trz, vaz = _train_z(train, valid, COMPOSITE_COLS)
    med = trz.median()
    score = vaz.fillna(med).mean(axis=1)
    return _to_unit(score.to_numpy())


def b4_position_percentile_composite(train, valid, **_):
    """ML_SPEC #4 — equal-weight composite of WITHIN-POSITION percentile ranks.
    Percentile reference distributions come from the training fold only."""
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
    return _to_unit(comp.fillna(0.5).mean(axis=1).to_numpy())


def _to_unit(x):
    """Monotone map of an arbitrary score to (0,1) so probability metrics are
    computable. Rank-preserving; NOT a calibrated probability."""
    s = pd.Series(x)
    r = s.rank(method="average", na_option="keep")
    n = r.notna().sum()
    out = (r - 0.5) / n
    return out.fillna(0.5).clip(1e-6, 1 - 1e-6).to_numpy()


# ------------------------------------------------------------------ metrics
def stage_a_metrics(y, p, low_support_threshold=5):
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


def board_metrics(y, p, ks, seed=20260808):
    """Precision@K / Recall@K / NDCG@K on the induced ranking.

    Ties are broken by a SEEDED random permutation, not by row order. Without
    this a constant predictor (B0) inherits the source ordering — and ML-0
    builds the population drafted-first, which would hand it a spurious
    NDCG of 1.0.
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
