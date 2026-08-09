#!/usr/bin/env python3
"""Backtest the FROZEN Stage A model on the historical folds. Thin CLI.

Stage A predicts P(drafted) for a declared NCAA early entrant. The methodology
is frozen (DEC-080..085) and this script evaluates it — it does not select it.
To re-run the selection experiment, use
scripts/experiments/ml4_stage_a_selection.py.

The 2026 holdout is never loaded.

  python scripts/run_stage_a.py
"""

import argparse
import math
import sys

import pandas as pd

from draftlens.ml.datasets import load_development
from draftlens.ml.metrics import (board_metrics, expected_calibration_error,
                                  stage_a_metrics)
from draftlens.ml.stage_a import STAGE_A, feature_set, fit_predict_fold
from draftlens.ml.validation import (LOW_SUPPORT_YEAR, folds, load_fold_config)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    cfg = load_fold_config()
    dev = load_development()
    feats = feature_set(STAGE_A["feature_set"], cfg)
    low = cfg["low_negative_support_threshold"]

    print(f"{'=' * 78}\nSTAGE A — FROZEN METHODOLOGY\n{'=' * 78}")
    for k, v in STAGE_A.items():
        print(f"  {k:<18} {v}")
    print(f"  {'features':<18} {len(feats)}")
    print(f"  development        {len(dev)} rows "
          f"({int(dev.drafted.sum())} drafted / "
          f"{int((dev.drafted == 0).sum())} undrafted)")

    rows, oof = [], []
    for fold, tr_years, vy in folds(cfg):
        train = dev[dev.draft_year.isin(tr_years)].reset_index(drop=True)
        valid = dev[dev.draft_year == vy].reset_index(drop=True)
        p, _ = fit_predict_fold(train, valid, feats)
        m = stage_a_metrics(valid.drafted, p, low)
        m.update(board_metrics(valid.drafted, p,
                               {"drafted": int(valid.drafted.sum()),
                                "top25": math.ceil(0.25 * len(valid))}))
        rows.append(dict(fold=fold, validate_year=vy, n_train=len(train), **m))
        oof.append(pd.DataFrame({"draft_year": vy, "y": valid.drafted.values,
                                 "p": p}))

    fold_df = pd.DataFrame(rows)
    oof_df = pd.concat(oof, ignore_index=True)
    cols = ["validate_year", "n", "n_train", "drafted", "undrafted", "roc_auc",
            "pr_auc", "brier", "ndcg_at_drafted", "low_negative_support"]
    print(f"\n{'=' * 78}\nPER-FOLD\n{'=' * 78}")
    print(fold_df[cols].to_string(index=False))

    scored = fold_df[fold_df.roc_auc.notna()]
    print(f"\n{'=' * 78}\nAGGREGATE (year-macro AND pooled — DEC-075)\n{'=' * 78}")
    print(f"  macro ROC-AUC     {scored.roc_auc.mean():.4f}")
    print(f"  pooled ROC-AUC    "
          f"{stage_a_metrics(oof_df.y, oof_df.p, low)['roc_auc']:.4f}")
    print(f"  macro Brier       {fold_df.brier.mean():.4f}")
    print(f"  macro NDCG        {fold_df.ndcg_at_drafted.mean():.4f}")
    print(f"  fold SD           {scored.roc_auc.std():.4f}")
    print(f"  worst year        {scored.roc_auc.min():.4f}")
    print(f"  ECE               {expected_calibration_error(oof_df.y, oof_df.p):.4f}")
    print(f"\n  {LOW_SUPPORT_YEAR} is LOW NEGATIVE SUPPORT and must not drive "
          f"any selection (DEC-075).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
