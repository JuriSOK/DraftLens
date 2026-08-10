#!/usr/bin/env python3
"""Exercise the three product APIs on one historical draft class. Thin CLI.

Historical-development only, for now: this demonstrates the General Board,
Team Need and NBA Comparables APIs before application integration. It is not
a user interface. The 2026 holdout is refused.

  python scripts/demo.py --year 2024
  python scripts/demo.py --year 2024 --profile SHOOTER --player "Zach Edey"
"""

import argparse
import sys
import warnings

import numpy as np

HOLDOUT_YEAR = 2026


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year", type=int, default=2024,
                    help="development draft class to demonstrate (default 2024)")
    ap.add_argument("--profile", default="SHOOTER",
                    help="Team Need profile to demonstrate")
    ap.add_argument("--player", default=None,
                    help="prospect to run NBA Comparables for (default: the "
                         "class's top Overall Score)")
    ap.add_argument("--top", type=int, default=8)
    a = ap.parse_args()

    if a.year == HOLDOUT_YEAR:
        print(f"  REFUSED: {HOLDOUT_YEAR} is the sealed holdout and cannot "
              f"be demonstrated.")
        return 1

    warnings.filterwarnings("ignore", category=RuntimeWarning)

    from board.order import DRAFT_ORDER, draft_sizes
    from board.order import fit_predict_fold as order_fold
    from board.probability import DRAFT_PROBABILITY, feature_set
    from board.probability import fit_predict_fold as probability_fold
    from board.scoring import build_board, rank_board
    from comparables.explanations import explain_comparables
    from comparables.reference import load_ncaa_reference, load_pool
    from comparables.similarity import (build_distance_reference,
                                        find_comparables, prepare_pool)
    from comparables.space import DIMENSION_NAMES, build_nba_space, build_ncaa_space
    from data.build import load_development
    from team_need.dimensions import compute_components, compute_dimensions
    from team_need.explanations import explain
    from team_need.profiles import profile_names
    from team_need.reference import PercentileReference
    from team_need.scoring import profile_fit, rank_fit
    from validation import folds, load_fold_config

    cfg = load_fold_config()
    dev = load_development()
    dev["draft_size"] = dev.draft_year.map(draft_sizes())
    feats = feature_set(DRAFT_PROBABILITY["feature_set"], cfg)
    if a.year not in set(dev.draft_year):
        print(f"  {a.year} is not a development class {sorted(set(dev.draft_year))}")
        return 1

    fold = next(((tr, vy) for _, tr, vy in folds(cfg) if vy == a.year), None)
    if fold is None:
        print(f"  {a.year} is not a validation year in the frozen fold design")
        return 1
    tr_years, vy = fold
    train = dev[dev.draft_year.isin(tr_years)].reset_index(drop=True)
    cls = dev[dev.draft_year == vy].reset_index(drop=True)
    train_drafted = train[train.drafted == 1].reset_index(drop=True)

    # ---------------------------------------------------------- General Board
    p_a, _ = probability_fold(train, cls, feats)
    p_b, _ = order_fold(train_drafted, cls, feats, family=DRAFT_ORDER["family"],
                        params={"alpha": DRAFT_ORDER["alpha"]},
                        target=DRAFT_ORDER["target"])
    board = build_board(p_a, p_b, cls.draft_size)
    board["player_name"] = cls.player_name.values
    board["position_3"] = cls.position_3.values
    ranked = rank_board(board)

    print(f"{'=' * 78}\nGENERAL DRAFT BOARD — {a.year} class ({len(cls)} prospects)\n{'=' * 78}")
    show = ranked.head(a.top)[["board_rank", "player_name", "overall_score",
                               "stage_a_probability", "stage_b_quality"]]
    print(show.to_string(index=False,
                         formatters={"stage_a_probability": "{:.3f}".format,
                                     "stage_b_quality": "{:.3f}".format}))

    # ------------------------------------------------------------- Team Need
    ref = PercentileReference()
    components, raw = compute_components(cls, ref)
    dims, coverage = compute_dimensions(cls, ref, components)
    scored = profile_fit(cls, a.profile.upper(), ref, components, dims, coverage)
    scored = scored.join(cls[["player_name", "position_3"]])
    tn_ranked = rank_fit(scored)

    print(f"\n{'=' * 78}\nTEAM NEED — {a.profile.upper()} — {a.year} class\n{'=' * 78}")
    show = tn_ranked.head(a.top)[["fit_rank", "player_name", "position_3",
                                  "fit_score", "eligibility_status"]]
    print(show.to_string(index=False))
    print(f"  (available profiles: {', '.join(profile_names())})")

    # ------------------------------------------------------- NBA Comparables
    pool = prepare_pool(load_pool())
    ncaa_ref = load_ncaa_reference()
    nba_dims, _ = build_nba_space(pool)
    ncaa_dims, _ = build_ncaa_space(dev, ncaa_ref)
    dist_ref = build_distance_reference(ncaa_dims, nba_dims, max_prospects=200)

    if a.player:
        m = cls.player_name.str.lower() == a.player.lower()
        if not m.any():
            print(f"\n  '{a.player}' is not in the {a.year} class")
            return 1
        i = cls.index[m][0]
    else:
        i = ranked.iloc[0].name
        i = cls.index[cls.player_name == ranked.iloc[0].player_name][0]
    name = cls.loc[i, "player_name"]
    dev_i = dev.index[(dev.draft_year == a.year)
                      & (dev.player_name == name)][0]
    r = find_comparables(ncaa_dims.loc[dev_i], pool, nba_dims,
                         prospect_name=name, distance_reference=dist_ref,
                         prospect_height=dev.loc[dev_i, "height"])
    r = explain_comparables(ncaa_dims.loc[dev_i], nba_dims, pool, r)

    print(f"\n{'=' * 78}\nNBA STATISTICAL COMPARABLES — {name}\n{'=' * 78}")
    if r["status"] != "OK":
        print(f"  COMPARABLES UNAVAILABLE — {r['reason']}")
    else:
        for c in r["comparables"]:
            print(f"   {c['rank']}. {c['nba_player_name']:<24} "
                  f"similarity {c['similarity_score']:3d}")

    print(f"\n{'=' * 78}")
    print("  Overall Score is a 0-100 ranking score, not a probability, not a "
          "pick.\n  Fit Score is peer-relative to the requested need only, "
          "independent of the board.\n  NBA comparables are descriptive "
          "resemblance only — not a projection.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
