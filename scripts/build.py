#!/usr/bin/env python3
"""Build every analytical artifact, in dependency order. Thin CLI.

    dataset -> features -> team_need reference -> comparables references

Population gates and leakage audits run on every build; a gate failure exits
non-zero rather than writing a quietly wrong dataset. The 2026 holdout is
never built here.

  python scripts/build.py              # everything, in order
  python scripts/build.py dataset
  python scripts/build.py features --reference
  python scripts/build.py team_need
  python scripts/build.py comparables

Three more stages exist, deliberately excluded from `all` — the one-time 2026
holdout replay (see src/replay.py) and the public application data export
(see src/app_export.py), which depends on the replay already having run:

  python scripts/build.py replay-2026        # PART A: target-free predictions
  python scripts/build.py replay-2026-eval   # PART B: unseal + evaluate
  python scripts/build.py app-data           # write app/public/data/draftlens_2026.json
"""

import argparse
import json
import sys

from paths import interim

HOLDOUT_YEAR = 2026


def build_dataset(years=None):
    from data.build import PARTITIONS, build_prospect_dataset

    parts = PARTITIONS
    if years:
        lo, hi = (years.split("-") + [years])[:2]
        want = set(range(int(lo), int(hi) + 1))
        parts = {k: [y for y in v if y in want] for k, v in PARTITIONS.items()}
        parts = {k: v for k, v in parts.items() if v}

    report, failures = build_prospect_dataset(parts)
    print(f"\n{'=' * 78}\nDATASET BUILD RESULT\n{'=' * 78}")
    for k, v in report["partitions"].items():
        print(f"  {k:<10} rows={v['rows']:<5} drafted={v['drafted']:<4} "
              f"undrafted={v['undrafted']:<4} match={v['match_rate_pct']}%")
    print(f"\n  gate failures: {len(failures)}")
    for g in failures:
        print(f"    FAIL {g}")
    return 1 if failures else 0


def build_features(reference=False):
    from features.basketball import EXPECTED_ROWS, PARTITIONS, assemble, feature_columns
    from features.reference import build_reference

    out = interim("features")
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

    if reference:
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


def build_team_need(years="2014-2025"):
    from team_need.reference import MIN_GAMES, MIN_MINUTES, REFERENCE_FILE, build_reference

    lo, hi = (years.split("-") + [years])[:2]
    yrs = list(range(int(lo), int(hi) + 1))
    if HOLDOUT_YEAR in yrs:
        print(f"  REFUSED: {HOLDOUT_YEAR} is the sealed holdout.")
        return 1

    print(f"{'=' * 78}\nNCAA PEER PERCENTILE REFERENCE (Team Need)\n{'=' * 78}")
    ref = build_reference(yrs)
    REFERENCE_FILE.parent.mkdir(parents=True, exist_ok=True)
    ref.to_parquet(REFERENCE_FILE, index=False)
    print(f"\n  seasons {ref.season.min()}-{ref.season.max()} | "
          f"metrics {ref.metric.nunique()} | groups "
          f"{sorted(ref.reference_group.unique())}")
    print(f"  filter: >= {MIN_MINUTES} minutes and >= {MIN_GAMES} games")
    print(f"  rows {len(ref)} -> {REFERENCE_FILE}")
    return 0


def build_comparables(ncaa_years="2014-2025",
                      representation="RECENT_MULTI_SEASON"):
    from comparables.reference import (MIN_GAMES, MIN_MINUTES, NCAA_MIN_GAMES,
                                       NCAA_MIN_MINUTES, NCAA_REFERENCE_FILE,
                                       REFERENCE_FILE, REFERENCE_SEASONS,
                                       build_ncaa_reference, build_pool)
    from comparables.space import COMMON_METRICS

    lo, hi = (ncaa_years.split("-") + [ncaa_years])[:2]
    years = list(range(int(lo), int(hi) + 1))
    if HOLDOUT_YEAR in years or HOLDOUT_YEAR in REFERENCE_SEASONS:
        print(f"  REFUSED: {HOLDOUT_YEAR} is the sealed holdout.")
        return 1

    print(f"{'=' * 78}\nNBA REFERENCE POOL\n{'=' * 78}")
    pool = build_pool(representation)
    REFERENCE_FILE.parent.mkdir(parents=True, exist_ok=True)
    pool.to_parquet(REFERENCE_FILE, index=False)
    print(f"  seasons {REFERENCE_SEASONS[0]}-{REFERENCE_SEASONS[-1]} | "
          f"eligibility >= {MIN_MINUTES} min and >= {MIN_GAMES} games")
    print(f"  representation {representation}")
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


STAGES = {
    "dataset": lambda a: build_dataset(a.years),
    "features": lambda a: build_features(a.reference),
    "team_need": lambda a: build_team_need(a.team_need_years),
    "comparables": lambda a: build_comparables(a.ncaa_years, a.representation),
}

# NOT included in "all" — these are explicit, one-time actions that must never
# fire by accident from a normal `python scripts/build.py` run. replay-2026
# generates the 2026 product output without touching any 2026 outcome;
# replay-2026-eval unseals the outcome and evaluates, and refuses to run
# unless replay-2026 already froze and hashed its predictions.
def _replay_2026(a):
    import replay
    replay.generate()
    return 0


def _replay_2026_eval(a):
    import replay
    replay.evaluate()
    return 0


def _app_data(a):
    import app_export
    path, digest, n = app_export.write_payload()
    print(f"  wrote {path.relative_to(app_export.ROOT)}")
    print(f"  prospects  {n}")
    print(f"  sha256     {digest}")
    return 0


REPLAY_STAGES = {
    "replay-2026": _replay_2026,
    "replay-2026-eval": _replay_2026_eval,
    "app-data": _app_data,
}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("stage", nargs="?", default="all",
                    choices=["all", *STAGES, *REPLAY_STAGES])
    ap.add_argument("--years", default=None,
                    help="dataset: restrict the build, e.g. 2014-2025")
    ap.add_argument("--reference", action="store_true",
                    help="features: also build NCAA reference distributions")
    ap.add_argument("--team-need-years", default="2014-2025", dest="team_need_years")
    ap.add_argument("--ncaa-years", default="2014-2025")
    ap.add_argument("--representation", default="RECENT_MULTI_SEASON",
                    choices=["LATEST_SEASON", "RECENT_MULTI_SEASON", "CAREER"])
    a = ap.parse_args()

    if a.stage in REPLAY_STAGES:
        return REPLAY_STAGES[a.stage](a)

    wanted = list(STAGES) if a.stage == "all" else [a.stage]
    for name in wanted:
        print(f"\n{'#' * 78}\n# {name.upper()}\n{'#' * 78}")
        rc = STAGES[name](a)
        if rc:
            return rc
    return 0


if __name__ == "__main__":
    sys.exit(main())
