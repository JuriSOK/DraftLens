"""Temporal validation protocol and the 2026 holdout firewall.

Random train/test splitting is PROHIBITED for final evaluation (DEC-012): it
would place same-year prospects and same-class team-mates on both sides of the
split and destroy the temporal guarantee. Every fold trains on draft years
strictly earlier than the year it validates.

Everything fitted inside a fold — imputation, scalers, percentile references,
feature selection, calibration — must be fitted on TRAINING years only
(ML_SPEC 11.2). This module owns the fold definitions so Stage A and Stage B
cannot drift apart.
"""

import json

from draftlens.paths import CONFIG_ML

HOLDOUT_YEAR = 2026
LOW_SUPPORT_YEAR = 2025   # Stage A: 26 drafted / 2 undrafted (DEC-075)

FOLD_CONFIG = CONFIG_ML / "ml3_baselines.json"


def load_fold_config(path=FOLD_CONFIG):
    """The frozen fold/feature-set configuration shared by ML-3, ML-4 and ML-5."""
    return json.loads(path.read_text())


def folds(cfg=None):
    """(fold_id, train_years, validate_year) tuples.

    Training is always strictly earlier than validation, and 2026 can appear on
    neither side. Both properties are asserted here rather than trusted.
    """
    cfg = cfg if cfg is not None else load_fold_config()
    out = []
    for f in cfg["folds"]:
        lo, hi = f["train"]
        vy = f["validate"]
        tr = list(range(lo, hi + 1))
        assert max(tr) < vy, "training years must precede the validation year"
        assert vy != HOLDOUT_YEAR and HOLDOUT_YEAR not in tr
        out.append((f["fold"], tr, vy))
    return out


def assert_no_holdout(df, where=""):
    """Hard guard: the 2026 holdout must never reach training or evaluation.

    Raises rather than warns. A silently-included holdout year would invalidate
    the single evaluation the holdout exists to provide (ML_SPEC 25).
    """
    import pandas as pd
    if HOLDOUT_YEAR in set(pd.Series(df["draft_year"]).unique()):
        raise AssertionError(f"HOLDOUT GUARD: {HOLDOUT_YEAR} reached {where}")
    return df
