#!/usr/bin/env python3
"""Statistical NBA comparables for a historical NCAA prospect. Thin CLI.

Returns exactly three NBA players whose statistical and role profiles most
resemble the prospect's. This is DESCRIPTIVE resemblance — not a projection,
not a ceiling, not a claim that the prospect will become anyone.

Development classes only. The 2026 holdout is refused.

  python scripts/run_comparables.py --player "Trae Young"
  python scripts/run_comparables.py --year 2024 --top 5
"""

import argparse
import sys
import warnings

import numpy as np
import pandas as pd

from draftlens.comparables.explanations import explain_comparables
from draftlens.comparables.reference import load_ncaa_reference, load_pool
from draftlens.comparables.similarity import (build_distance_reference,
                                              find_comparables, prepare_pool)
from draftlens.comparables.space import (DIMENSION_NAMES, build_nba_space,
                                         build_ncaa_space)
from draftlens.ml.datasets import load_development

HOLDOUT_YEAR = 2026


def show(name, year, prospect_row, result):
    print(f"\n{'=' * 78}\n{name}  ({year})\n{'=' * 78}")
    print("  profile percentile vs NCAA peers:")
    for d in DIMENSION_NAMES:
        v = prospect_row.get(d, np.nan)
        print(f"    {d:24s} {'n/a' if not np.isfinite(v) else f'{v:5.0f}'}")
    if result["status"] != "OK":
        print(f"\n  COMPARABLES UNAVAILABLE — {result['reason']}")
        return
    print(f"\n  Statistical NBA comparables (descriptive resemblance only):")
    for c in result["comparables"]:
        seasons = "-".join(str(s) for s in
                           (c["reference_seasons"][0],
                            c["reference_seasons"][-1]))
        print(f"\n   {c['rank']}. {c['nba_player_name']:<24} "
              f"similarity {c['similarity_score']:3d}   "
              f"(NBA {seasons}, distance {c['raw_distance']:.1f})")
        for d in c["closest_dimensions"]:
            print(f"        ~ {d['label']}: {d['prospect_percentile']:.0f} vs "
                  f"{d['nba_percentile']:.0f}")
        for d in c["largest_differences"]:
            print(f"        ! {d['label']}: {d['prospect_percentile']:.0f} vs "
                  f"{d['nba_percentile']:.0f}")
    m = result.get("third_vs_fourth_margin")
    print(f"\n  3rd-vs-4th margin {m}   pool {result['pool_size']}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--player", help="prospect name (development classes only)")
    ap.add_argument("--year", type=int, help="show a class's prospects")
    ap.add_argument("--top", type=int, default=5,
                    help="how many prospects to show with --year")
    a = ap.parse_args()
    if not a.player and not a.year:
        ap.error("give --player or --year")
    if a.year == HOLDOUT_YEAR:
        print(f"  REFUSED: {HOLDOUT_YEAR} is the sealed holdout and is not "
              f"scored in ML-8.")
        return 1

    warnings.filterwarnings("ignore", category=RuntimeWarning)
    dev = load_development()
    pool = prepare_pool(load_pool())
    ncaa_ref = load_ncaa_reference()
    nba_dims, _ = build_nba_space(pool)
    ncaa_dims, _ = build_ncaa_space(dev, ncaa_ref)
    dist_ref = build_distance_reference(ncaa_dims, nba_dims, max_prospects=300)

    if a.player:
        m = dev.player_name.str.lower() == a.player.lower()
        if not m.any():
            print(f"  '{a.player}' is not in the development population")
            return 1
        rows = dev.index[m][:1]
    else:
        if a.year not in set(dev.draft_year):
            print(f"  {a.year} is not a development class "
                  f"{sorted(set(dev.draft_year))}")
            return 1
        rows = dev.index[dev.draft_year == a.year][:a.top]

    for i in rows:
        name = dev.loc[i, "player_name"]
        r = find_comparables(ncaa_dims.loc[i], pool, nba_dims,
                             prospect_name=name, distance_reference=dist_ref)
        r = explain_comparables(ncaa_dims.loc[i], nba_dims, pool, r)
        show(name, int(dev.loc[i, "draft_year"]), ncaa_dims.loc[i], r)

    print(f"\n{'=' * 78}")
    print("  These are STATISTICAL RESEMBLANCES between pre-draft NCAA profiles")
    print("  and recent NBA role profiles. They are not projections, ceilings,")
    print("  floors, or claims about what any prospect will become.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
