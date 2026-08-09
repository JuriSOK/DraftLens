#!/usr/bin/env python3
"""Backtest the FROZEN Stage B ranker on the historical folds. Thin CLI.

Stage B ranks DRAFTED early entrants by how highly their pre-draft profile
suggests they be selected. The methodology is frozen (DEC-086..091) and this
script evaluates it — it does not select it. To re-run the selection experiment,
use scripts/experiments/ml5_stage_b_selection.py.

Stage B output is an ORDERING. The numeric predicted pick is NOT display-safe
(DEC-089) and is printed here only as diagnostic error magnitude.

The 2026 holdout is never loaded.

  python scripts/run_stage_b.py
"""

import argparse
import sys

import pandas as pd

from draftlens.ml.datasets import load_stage_b
from draftlens.ml.metrics import stage_b_metrics
from draftlens.ml.stage_a import feature_set
from draftlens.ml.stage_b import STAGE_B, draft_sizes, fit_predict_fold
from draftlens.ml.validation import folds, load_fold_config


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.parse_args()

    cfg = load_fold_config()
    sizes = draft_sizes()
    dev = load_stage_b()
    dev["draft_size"] = dev.draft_year.map(sizes)
    feats = feature_set(STAGE_B["feature_set"], cfg)

    print(f"{'=' * 78}\nSTAGE B — FROZEN METHODOLOGY\n{'=' * 78}")
    for k, v in STAGE_B.items():
        print(f"  {k:<18} {v}")
    print(f"  {'features':<18} {len(feats)}")
    print(f"  population         {len(dev)} drafted early entrants "
          f"({int((dev.drafted == 0).sum())} undrafted — must be 0)")

    rows = []
    for fold, tr_years, vy in folds(cfg):
        train = dev[dev.draft_year.isin(tr_years)].reset_index(drop=True)
        valid = dev[dev.draft_year == vy].reset_index(drop=True)
        pred, _ = fit_predict_fold(train, valid, feats,
                                   family=STAGE_B["family"],
                                   params={"alpha": STAGE_B["alpha"]},
                                   target=STAGE_B["target"])
        m = stage_b_metrics(valid.pick, pred, valid.draft_size)
        rows.append(dict(validate_year=vy, n_train=len(train), **m))

    fold_df = pd.DataFrame(rows)
    cols = ["validate_year", "n", "n_train", "spearman", "kendall_tau", "ndcg",
            "ndcg_at_14", "mae_pick", "rmse_pick", "lottery_recall_at_14"]
    print(f"\n{'=' * 78}\nPER-FOLD\n{'=' * 78}")
    print(fold_df[cols].to_string(index=False))

    print(f"\n{'=' * 78}\nAGGREGATE — RANKING FIRST (DEC-088)\n{'=' * 78}")
    print(f"  macro Spearman    {fold_df.spearman.mean():.4f}")
    print(f"  macro Kendall     {fold_df.kendall_tau.mean():.4f}")
    print(f"  macro NDCG        {fold_df.ndcg.mean():.4f}")
    print(f"  macro NDCG@14     {fold_df.ndcg_at_14.mean():.4f}")
    print(f"  fold SD           {fold_df.spearman.std():.4f}")
    print(f"  worst year        {fold_df.spearman.min():.4f}")
    print(f"  macro MAE (picks) {fold_df.mae_pick.mean():.4f}   <- supporting only")
    print(f"  macro RMSE        {fold_df.rmse_pick.mean():.4f}   <- supporting only")
    print("\n  Board figures cover IN-SCOPE NCAA EARLY ENTRANTS only — not "
          "seniors,\n  not international prospects. The numeric pick is not "
          "display-safe (DEC-089).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
