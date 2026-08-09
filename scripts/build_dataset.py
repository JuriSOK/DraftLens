#!/usr/bin/env python3
"""Build the ML-0 model-ready prospect dataset. Thin CLI.

Population gates and leakage audits run on every build; a gate failure exits
non-zero rather than writing a quietly wrong dataset.

  python scripts/build_dataset.py
  python scripts/build_dataset.py --years 2014-2025
"""

import argparse
import sys

from draftlens.data.dataset import PARTITIONS, build_prospect_dataset


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--years", default=None,
                    help="restrict the build, e.g. 2014-2025 (default: all)")
    a = ap.parse_args()

    parts = PARTITIONS
    if a.years:
        lo, hi = (a.years.split("-") + [a.years])[:2]
        want = set(range(int(lo), int(hi) + 1))
        parts = {k: [y for y in v if y in want] for k, v in PARTITIONS.items()}
        parts = {k: v for k, v in parts.items() if v}

    report, failures = build_prospect_dataset(parts)
    print(f"\n{'=' * 78}\nML-0 BUILD RESULT\n{'=' * 78}")
    for k, v in report["partitions"].items():
        print(f"  {k:<10} rows={v['rows']:<5} drafted={v['drafted']:<4} "
              f"undrafted={v['undrafted']:<4} match={v['match_rate_pct']}%")
    print(f"\n  gate failures: {len(failures)}")
    for g in failures:
        print(f"    FAIL {g}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
