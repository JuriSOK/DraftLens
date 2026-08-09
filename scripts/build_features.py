#!/usr/bin/env python3
"""Build the basketball feature layer. Thin CLI over draftlens.features.

  python scripts/build_features.py
  python scripts/build_features.py --reference   (also rebuild the NCAA
      season x position reference distributions the SEASON_RELATIVE
      representation depends on; slower)
"""

import argparse
import json
import sys

import pandas as pd

from draftlens.features.engineering import (EXPECTED_ROWS, PARTITIONS, assemble,
                                            feature_columns)
from draftlens.features.reference import build_reference
from draftlens.paths import interim


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reference", action="store_true",
                    help="also build NCAA season x position reference distributions")
    a = ap.parse_args()
    out = interim("ml2")
    report = {}

    for label, years in PARTITIONS.items():
        print(f"\n{'=' * 78}\nPARTITION {label}\n{'=' * 78}")
        df = assemble(label, years)
        expected = EXPECTED_ROWS[label]
        if len(df) != expected:
            print(f"  rows={len(df)} expected={expected} -> MISMATCH")
            return 1
        feats = feature_columns(df)
        df.to_parquet(out / f"features_{label}.parquet", index=False)
        report[label] = dict(rows=len(df), engineered_features=len(feats))
        print(f"  rows={len(df)} engineered={len(feats)} -> wrote "
              f"features_{label}.parquet")

    if a.reference:
        print(f"\n{'=' * 78}\nNCAA REFERENCE DISTRIBUTIONS\n{'=' * 78}")
        years = sorted({y for ys in PARTITIONS.values() for y in ys})
        ref = build_reference(years)
        ref.to_parquet(out / "ncaa_reference_distributions.parquet", index=False)
        print(f"  rows={len(ref)} seasons={ref.season.nunique()} "
              f"metrics={ref.metric.nunique()}")
        report["reference_rows"] = len(ref)

    (out / "quality_report.json").write_text(json.dumps(report, indent=2,
                                                        default=str))
    print(f"\n  outputs -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
