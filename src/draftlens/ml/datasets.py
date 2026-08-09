"""Model-ready dataset loading, with the holdout firewall built in.

`load_development` and `load_robustness` are the ONLY approved ways to obtain
labelled data for modelling. Both assert that 2026 is absent, so a phase cannot
accidentally train on the holdout by importing the wrong parquet file.

The 2026 partition is deliberately NOT loadable from this module.
"""

import pandas as pd

from draftlens.leakage import DENIED, DENIED_SUBSTR
from draftlens.ml.validation import HOLDOUT_YEAR, assert_no_holdout
from draftlens.paths import INTERIM

ML0 = INTERIM / "ml0"
ML2 = INTERIM / "ml2"


def _labelled(features_file, targets_file):
    f = pd.read_parquet(ML2 / features_file)
    t = pd.read_parquet(ML0 / targets_file)
    m = f.merge(t[["canonical_prospect_id", "drafted", "pick"]],
                on="canonical_prospect_id", how="inner")
    assert HOLDOUT_YEAR not in set(m.draft_year), "HOLDOUT GUARD: 2026 present"
    return m


def load_development():
    """ML-2 features joined to development targets, 2014-2025. 887 prospects."""
    return _labelled("features_2014_2025.parquet", "targets_2014_2025.parquet")


def load_robustness():
    """2011-2013. Sensitivity analysis only — never the default training set,
    and never permitted to influence a selection decision (ML_SPEC 4.1)."""
    return _labelled("features_2011_2013.parquet", "targets_2011_2013.parquet")


def load_stage_b(robustness=False):
    """Drafted early entrants only — the Stage B population (431 in 2014-2025).

    Undrafted prospects are REMOVED, never relabelled. Assigning them a sentinel
    pick (61, 100, 999) would invent data and distort the loss surface
    (ML_SPEC 6.2, DEC-017), so a row without a real pick cannot reach Stage B.
    """
    df = load_robustness() if robustness else load_development()
    d = df[df.drafted == 1].copy()
    assert d.pick.notna().all(), "a drafted prospect has no pick — refusing to invent one"
    assert_no_holdout(d, "stage B")
    d["pick"] = d["pick"].astype(int)
    return d.reset_index(drop=True)


def resolve_features(cfg, name, train_df, strategy):
    """Feature list for a set + missing strategy, decided on TRAINING data only.

    `C_HIGH_COVERAGE` thresholds on training coverage specifically: using the
    full pool would let validation-year availability influence which columns the
    model may see.
    """
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
