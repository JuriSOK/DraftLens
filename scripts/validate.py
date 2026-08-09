#!/usr/bin/env python3
"""Run DraftLens validation. Thin CLI dispatcher.

Each stage has its own validator because their rules genuinely differ; the
assertions they share live in `draftlens.ml.guards`. Consolidating file count
at the cost of a weaker check is not a trade this project makes.

  python scripts/validate.py              # everything except raw checksums
  python scripts/validate.py --stage raw  # raw corpus + manifest integrity
  python scripts/validate.py --stage ml5
"""

import argparse
import subprocess
import sys

from draftlens.paths import ROOT

EXPERIMENTS = ROOT / "scripts" / "experiments"

STAGES = {
    "ml0": EXPERIMENTS / "validate_ml0_dataset.py",
    "ml2": EXPERIMENTS / "validate_ml2_features.py",
    "ml3": EXPERIMENTS / "validate_ml3_baselines.py",
    "ml4": EXPERIMENTS / "validate_ml4_stage_a.py",
    "ml5": EXPERIMENTS / "validate_ml5_stage_b.py",
    "ml6": EXPERIMENTS / "validate_ml6_board.py",
}
# Raw validation needs the 200 MB corpus present, so it is opt-in.
RAW_STAGE = "raw"


def run_raw():
    from draftlens.data.validation import raw
    return raw.main()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage", default="all",
                    choices=["all", RAW_STAGE, *STAGES],
                    help="which validator to run (default: all analytical stages)")
    a = ap.parse_args()

    if a.stage == RAW_STAGE:
        return run_raw()

    wanted = list(STAGES) if a.stage == "all" else [a.stage]
    results = {}
    for name in wanted:
        print(f"\n{'#' * 78}\n# {name.upper()}\n{'#' * 78}")
        r = subprocess.run([sys.executable, str(STAGES[name])], cwd=ROOT)
        results[name] = r.returncode

    print(f"\n{'=' * 78}\nVALIDATION SUMMARY\n{'=' * 78}")
    for name, code in results.items():
        print(f"  {name:<6} {'PASS' if code == 0 else 'FAIL'}")
    failed = [n for n, c in results.items() if c]
    print(f"\n  {len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
