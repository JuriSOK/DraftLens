"""ML-3 validation — hard-fails on population loss, leakage or holdout bleed.

  ./.venv/bin/python scripts/validate_ml3_results.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ml3_common import (DENIED, DENIED_SUBSTR, HOLDOUT_YEAR, OUT,  # noqa: E402
                        folds, load_config, load_development)

FAIL, WARN = [], []
CFG = load_config()


def rule(t):
    print(f"\n{'=' * 78}\n{t}\n{'=' * 78}")


def check(cond, msg, hard=True):
    if cond:
        return True
    (FAIL if hard else WARN).append(msg)
    print(f"  {'FAIL' if hard else 'WARN'}  {msg}")
    return False


def main():
    rule("ML-3 VALIDATION")
    if not (OUT / "fold_results.csv").exists():
        print("  FAIL  ML-3 outputs missing — run run_ml3_baselines.py")
        return 1

    dev = load_development()
    fold_df = pd.read_csv(OUT / "fold_results.csv")
    oof = pd.read_parquet(OUT / "oof_predictions.parquet")

    # population
    check(len(dev) == 887, f"development population is {len(dev)}, expected 887")
    check(int(dev.drafted.sum()) == 431, "drafted count changed")
    check(int((dev.drafted == 0).sum()) == 456, "undrafted count changed")
    unresolved = int(dev.hoopr_athlete_id.isna().sum())
    check(unresolved >= 8, f"unresolved prospects lost ({unresolved})")
    print(f"  development 887 / 431 / 456 | unresolved retained {unresolved}")

    # holdout firewall
    check(HOLDOUT_YEAR not in set(dev.draft_year), "2026 present in development")
    check(HOLDOUT_YEAR not in set(fold_df.validate_year),
          "2026 appears as a validation year")
    check(HOLDOUT_YEAR not in set(oof.draft_year),
          "2026 appears in out-of-fold predictions")
    check(not any(str(HOLDOUT_YEAR) in str(t) for t in fold_df.train_years),
          "2026 appears in a training range")
    for f in CFG["folds"]:
        check(HOLDOUT_YEAR not in range(f["train"][0], f["train"][1] + 1),
              f"fold {f['fold']} trains on 2026")
        check(f["validate"] != HOLDOUT_YEAR, f"fold {f['fold']} validates 2026")
    print("  holdout firewall: 2026 absent from folds, training, and predictions")

    # temporal ordering
    for fold, tr, vy in folds(CFG):
        check(max(tr) < vy, f"fold {fold}: training year >= validation year")
    print("  temporal ordering: every training year precedes its validation year")

    # feature safety
    bad_sets = {}
    for name, feats in CFG["feature_sets"].items():
        bad = [c for c in feats if c in DENIED
               or any(s in c.lower() for s in DENIED_SUBSTR)]
        if bad:
            bad_sets[name] = bad
    check(not bad_sets, f"denied features present in feature sets: {bad_sets}")
    print(f"  feature sets clean: {len(CFG['feature_sets'])} sets checked")

    # every eligible validation row got a prediction, none dropped
    for name, g in oof.groupby("config"):
        for vy, gg in g.groupby("draft_year"):
            expect = int((dev.draft_year == vy).sum())
            check(len(gg) == expect,
                  f"{name} {vy}: {len(gg)} predictions for {expect} prospects "
                  f"— rows were dropped")
            check(gg.p.notna().all(), f"{name} {vy}: null predictions")
            check(((gg.p >= 0) & (gg.p <= 1)).all(),
                  f"{name} {vy}: predictions outside [0,1]")
    print(f"  predictions complete for all {oof.config.nunique()} configs "
          f"— no complete-case dropping")

    # unresolved prospects must still receive predictions
    unresolved_ids = set(dev[dev.hoopr_athlete_id.isna()].canonical_prospect_id)
    for name, g in oof.groupby("config"):
        covered = unresolved_ids & set(g.canonical_prospect_id)
        eligible = {i for i in unresolved_ids
                    if dev.loc[dev.canonical_prospect_id == i, "draft_year"]
                    .iloc[0] in set(fold_df.validate_year)}
        check(eligible <= covered,
              f"{name}: unresolved prospects missing predictions "
              f"({len(eligible - covered)})")
    print("  unresolved prospects received predictions (not dropped)")

    # low-support flag present where expected
    ls = fold_df[fold_df.validate_year == 2025].low_negative_support
    check(bool(ls.all()), "2025 not flagged LOW NEGATIVE SUPPORT")
    print("  2025 flagged LOW NEGATIVE SUPPORT")

    # no holdout predictions written anywhere
    for p in OUT.glob("*"):
        if p.suffix in (".csv", ".parquet"):
            df = pd.read_csv(p) if p.suffix == ".csv" else pd.read_parquet(p)
            for col in ("draft_year", "validate_year"):
                if col in df.columns:
                    check(HOLDOUT_YEAR not in set(df[col].dropna()),
                          f"{p.name}: contains {HOLDOUT_YEAR} in {col}")
    print("  no generated artifact contains holdout rows")

    rule("RESULT")
    print(f"  hard failures: {len(FAIL)}\n  warnings     : {len(WARN)}")
    for m in FAIL:
        print(f"   FAIL {m}")
    for m in WARN:
        print(f"   WARN {m}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
