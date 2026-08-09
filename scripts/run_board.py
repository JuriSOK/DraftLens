#!/usr/bin/env python3
"""Build the General Draft Board on historical folds. Thin CLI.

Combines the frozen Stage A and Stage B signals using the frozen ML-6 board
method and prints the resulting board for one development validation year.

This EVALUATES the frozen methodology; it does not select it. To re-run the
selection experiment use scripts/experiments/ml6_board_selection.py.

The 2026 holdout is never loaded.

  python scripts/run_board.py                 # summary across all folds
  python scripts/run_board.py --year 2024     # show that class's board
"""

import argparse
import sys

import numpy as np
import pandas as pd

from draftlens.ml.board import (BOARD, build_board, graded_relevance,
                                rank_board)
from draftlens.ml.datasets import load_development
from draftlens.ml.metrics import (board_binary_metrics, board_graded_metrics,
                                  board_order_metrics)
from draftlens.ml.stage_a import STAGE_A, feature_set
from draftlens.ml.stage_a import fit_predict_fold as stage_a_fold
from draftlens.ml.stage_b import STAGE_B, draft_sizes
from draftlens.ml.stage_b import fit_predict_fold as stage_b_fold
from draftlens.ml.validation import LOW_SUPPORT_YEAR, folds, load_fold_config


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year", type=int, default=None,
                    help="show the full board for one validation year")
    ap.add_argument("--top", type=int, default=15,
                    help="rows to display when --year is given")
    a = ap.parse_args()

    cfg = load_fold_config()
    dev = load_development()
    dev["draft_size"] = dev.draft_year.map(draft_sizes())
    feats = feature_set(STAGE_A["feature_set"], cfg)

    print(f"{'=' * 78}\nGENERAL DRAFT BOARD — FROZEN METHOD\n{'=' * 78}")
    for k, v in BOARD.items():
        print(f"  {k:<20} {v}")
    print(f"  {'stage A':<20} {STAGE_A['family']} C={STAGE_A['C']} "
          f"{STAGE_A['normalization']}")
    print(f"  {'stage B':<20} {STAGE_B['family']} alpha={STAGE_B['alpha']} "
          f"{STAGE_B['normalization']}")

    rows, boards = [], {}
    for _, tr_years, vy in folds(cfg):
        tr_all = dev[dev.draft_year.isin(tr_years)].reset_index(drop=True)
        va = dev[dev.draft_year == vy].reset_index(drop=True)
        tr_drafted = tr_all[tr_all.drafted == 1].reset_index(drop=True)

        p_a, _ = stage_a_fold(tr_all, va, feats)
        p_b, _ = stage_b_fold(tr_drafted, va, feats, family=STAGE_B["family"],
                              params={"alpha": STAGE_B["alpha"]},
                              target=STAGE_B["target"])
        b = build_board(p_a, p_b, va.draft_size)
        b["draft_year"] = vy
        b["player_name"] = va.player_name.values
        b["actual_drafted"] = va.drafted.values
        b["actual_pick"] = va.pick.values
        boards[vy] = b

        rel = graded_relevance(va.drafted, va.pick, va.draft_size)
        sig = b.final_board_signal.to_numpy()
        ks = {"drafted": int(va.drafted.sum()),
              "top25": int(np.ceil(0.25 * len(va)))}
        m = dict(validate_year=vy)
        m.update(board_binary_metrics(va.drafted, sig, ks))
        m.update(board_graded_metrics(rel, sig))
        d = (va.drafted == 1).to_numpy()
        m.update(board_order_metrics(va.pick[d], sig[d]))
        rows.append(m)

    fold_df = pd.DataFrame(rows)

    if a.year:
        if a.year not in boards:
            print(f"\n  {a.year} is not a development validation year "
                  f"{sorted(boards)}")
            return 1
        b = rank_board(boards[a.year])
        print(f"\n{'=' * 78}\n{a.year} BOARD — top {a.top} of {len(b)}\n{'=' * 78}")
        show = b.head(a.top)[["board_rank", "player_name", "overall_score",
                              "stage_a_probability", "stage_b_quality",
                              "actual_drafted", "actual_pick"]]
        print(show.to_string(index=False,
                             formatters={"stage_a_probability": "{:.3f}".format,
                                         "stage_b_quality": "{:.3f}".format}))
        print("\n  overall_score is a 0-100 RANKING score, not a probability "
              "and not a pick.")
        return 0

    cols = ["validate_year", "n", "drafted", "roc_auc", "average_precision",
            "graded_ndcg", "drafted_spearman", "drafted_kendall",
            "precision_at_drafted", "low_negative_support"]
    print(f"\n{'=' * 78}\nPER-FOLD\n{'=' * 78}")
    print(fold_df[cols].to_string(index=False))

    scored = fold_df[fold_df.roc_auc.notna()]
    print(f"\n{'=' * 78}\nAGGREGATE\n{'=' * 78}")
    print(f"  binary macro ROC-AUC   {scored.roc_auc.mean():.4f}")
    print(f"  macro average precision{scored.average_precision.mean():>8.4f}")
    print(f"  graded NDCG            {fold_df.graded_ndcg.mean():.4f}")
    print(f"  drafted-only Spearman  {fold_df.drafted_spearman.mean():.4f}")
    print(f"  drafted-only Kendall   {fold_df.drafted_kendall.mean():.4f}")
    print(f"  graded NDCG fold SD    {fold_df.graded_ndcg.std():.4f}")
    print(f"  graded NDCG worst year {fold_df.graded_ndcg.min():.4f}")
    print(f"\n  {LOW_SUPPORT_YEAR} has 2 undrafted prospects — its BINARY "
          f"metrics are unstable\n  and must not drive any selection "
          f"(DEC-075). Its draft-order metrics are sound.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
