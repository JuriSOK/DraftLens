#!/usr/bin/env python3
"""Build the NCAA peer percentile reference Team Need scores against. Thin CLI.

The reference is the FULL NCAA player population of each season, filtered to
players with a season's worth of evidence. No draft outcome is read.

  python scripts/build_team_need_reference.py
"""

import argparse
import sys

from draftlens.team_need.reference import (MIN_GAMES, MIN_MINUTES,
                                           REFERENCE_FILE, build_reference)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--years", default="2014-2025",
                    help="development window (default 2014-2025); the 2026 "
                         "holdout is not built here")
    a = ap.parse_args()
    lo, hi = (a.years.split("-") + [a.years])[:2]
    years = list(range(int(lo), int(hi) + 1))
    if 2026 in years:
        print("  REFUSED: 2026 is the sealed holdout and is not built in ML-7.")
        return 1

    print(f"{'=' * 78}\nNCAA PEER PERCENTILE REFERENCE\n{'=' * 78}")
    ref = build_reference(years)
    REFERENCE_FILE.parent.mkdir(parents=True, exist_ok=True)
    ref.to_parquet(REFERENCE_FILE, index=False)
    print(f"\n  seasons {ref.season.min()}-{ref.season.max()} | "
          f"metrics {ref.metric.nunique()} | groups "
          f"{sorted(ref.reference_group.unique())}")
    print(f"  filter: >= {MIN_MINUTES} minutes and >= {MIN_GAMES} games")
    print(f"  rows {len(ref)} -> {REFERENCE_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
