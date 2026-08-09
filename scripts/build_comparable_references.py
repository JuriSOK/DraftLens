#!/usr/bin/env python3
"""Build the NCAA and NBA peer references comparables are computed against.

Two populations, each defining "peers" for its own league. No draft outcome and
no NBA career result is read by either.

The 2026 holdout is excluded from both.

  python scripts/build_comparable_references.py
"""

import argparse
import sys

from draftlens.comparables.reference import (MIN_GAMES, MIN_MINUTES,
                                             NCAA_MIN_GAMES, NCAA_MIN_MINUTES,
                                             NCAA_REFERENCE_FILE,
                                             REFERENCE_FILE, REFERENCE_SEASONS,
                                             build_ncaa_reference, build_pool)
from draftlens.comparables.space import COMMON_METRICS

HOLDOUT_YEAR = 2026


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ncaa-years", default="2014-2025")
    ap.add_argument("--representation", default="RECENT_MULTI_SEASON",
                    choices=["LATEST_SEASON", "RECENT_MULTI_SEASON", "CAREER"])
    a = ap.parse_args()
    lo, hi = (a.ncaa_years.split("-") + [a.ncaa_years])[:2]
    years = list(range(int(lo), int(hi) + 1))
    if HOLDOUT_YEAR in years or HOLDOUT_YEAR in REFERENCE_SEASONS:
        print(f"  REFUSED: {HOLDOUT_YEAR} is the sealed holdout.")
        return 1

    print(f"{'=' * 78}\nNBA REFERENCE POOL\n{'=' * 78}")
    pool = build_pool(a.representation)
    REFERENCE_FILE.parent.mkdir(parents=True, exist_ok=True)
    pool.to_parquet(REFERENCE_FILE, index=False)
    print(f"  seasons {REFERENCE_SEASONS[0]}-{REFERENCE_SEASONS[-1]} | "
          f"eligibility >= {MIN_MINUTES} min and >= {MIN_GAMES} games")
    print(f"  representation {a.representation}")
    print(f"  {len(pool)} unique NBA players -> {REFERENCE_FILE.name}")

    print(f"\n{'=' * 78}\nNCAA PEER REFERENCE\n{'=' * 78}")
    ncaa = build_ncaa_reference(years)
    ncaa.to_parquet(NCAA_REFERENCE_FILE, index=False)
    print(f"  eligibility >= {NCAA_MIN_MINUTES} min and >= {NCAA_MIN_GAMES} games")
    print(f"  {len(ncaa)} player-seasons across {ncaa.season.nunique()} seasons "
          f"-> {NCAA_REFERENCE_FILE.name}")
    print(f"\n  common metrics ({len(COMMON_METRICS)}): "
          f"{', '.join(COMMON_METRICS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
