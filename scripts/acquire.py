#!/usr/bin/env python3
"""Acquire raw source data. Thin CLI over `data.hoopr` / `data.wikipedia`.

Raw files are immutable: an existing file is never overwritten unless --force.
Nothing here is required to inspect the analytical results, but re-running it
reproduces the raw corpus (~200 MB, git-ignored).

  python scripts/acquire.py mbb --years 2011-2026
  python scripts/acquire.py population --years 2011-2026 --wikidata
  python scripts/acquire.py declared --years 2026
"""

import argparse
import sys

from data import hoopr, wikipedia


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", choices=["mbb", "nba", "all", "population", "declared"],
                    help="hoopR dataset family, the Wikipedia FINAL draft "
                        "population, or the ORIGINAL declared pool "
                        "(pre-withdrawal, see data.wikipedia.DECLARED_SNAPSHOTS)")
    ap.add_argument("--years", default="2011-2026")
    ap.add_argument("--force", action="store_true",
                    help="re-download files that already exist")
    ap.add_argument("--wikidata", action="store_true",
                    help="population only: also enrich from Wikidata (CC0)")
    a = ap.parse_args()

    years = hoopr.parse_years(a.years)
    if a.source == "population":
        return wikipedia.acquire(years, wikidata=a.wikidata)
    if a.source == "declared":
        return wikipedia.acquire_declared(years)
    sources = ["mbb", "nba"] if a.source == "all" else [a.source]
    for s in sources:
        hoopr.acquire(s, years, force=a.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
