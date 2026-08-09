"""ML-0 validation — fails loudly on population, leakage, or integrity errors.

Run after scripts/build_model_dataset.py. Exits non-zero on any hard failure.

  ./.venv/bin/python scripts/experiments/validate_ml0_dataset.py
"""

import json
import sys
from pathlib import Path

import pandas as pd

from draftlens.data.dataset import PARTITIONS, build_year
from draftlens.data.population import EXPECTED, load_population, load_targets
from draftlens.data.identity.matching import load_overrides
from draftlens.leakage import (DENY_EXACT, DENY_SUBSTRING, SUSPICIOUS,
                               SUSPICIOUS_ALLOWED)
from draftlens.paths import interim

OUT = interim("ml0")


FAIL, WARN = [], []


def rule(t):
    print(f"\n{'=' * 78}\n{t}\n{'=' * 78}")


def check(cond, msg, hard=True):
    if cond:
        return True
    (FAIL if hard else WARN).append(msg)
    print(f"  {'FAIL' if hard else 'WARN'}  {msg}")
    return False


def load(label):
    f = pd.read_parquet(OUT / f"features_{label}.parquet")
    t = pd.read_parquet(OUT / f"targets_{label}.parquet")
    return f, t


def main():
    rule("ML-0 VALIDATION")
    if not (OUT / "features_2014_2025.parquet").exists():
        print("  FAIL  ML-0 outputs not found — run build_model_dataset.py first")
        return 1

    all_ids = {}
    for label, years in PARTITIONS.items():
        print(f"\n--- partition {label} ---")
        feats, tgt = load(label)

        # 1. population gates
        exp = EXPECTED.get(label)
        if exp:
            n, nd = len(feats), int(tgt.drafted.sum())
            nu = int((tgt.drafted == 0).sum())
            check(n == exp[0], f"{label}: expected {exp[0]} rows, got {n}")
            if exp[1] is not None:
                check(nd == exp[1], f"{label}: expected {exp[1]} drafted, got {nd}")
                check(nu == exp[2], f"{label}: expected {exp[2]} undrafted, got {nu}")
            print(f"  population: {n} rows, {nd} drafted, {nu} undrafted")

        # 2. duplicate canonical prospects
        check(not feats.canonical_prospect_id.duplicated().any(),
              f"{label}: duplicate canonical_prospect_id in features")
        check(not tgt.canonical_prospect_id.duplicated().any(),
              f"{label}: duplicate canonical_prospect_id in targets")

        # 3. feature/target key alignment
        fk, tk = set(feats.canonical_prospect_id), set(tgt.canonical_prospect_id)
        check(fk == tk, f"{label}: feature/target keys differ "
                        f"(features-only={len(fk-tk)}, targets-only={len(tk-fk)})")

        # 4. LEAKAGE — no outcome/age column in the feature file
        cols = [c.lower() for c in feats.columns]
        denied = [c for c in cols if c in DENY_EXACT
                  or any(s in c for s in DENY_SUBSTRING)]
        check(not denied, f"{label}: PROHIBITED columns in feature file: {denied}")
        susp = [c for c in cols if any(s in c for s in SUSPICIOUS)
                and c not in SUSPICIOUS_ALLOWED and c not in denied]
        if susp:
            print(f"  note: suspicious-but-reviewed column names: {susp}")

        # 5. sampling frame — every row must be a final early entrant
        check("early_entrant" not in cols,
              f"{label}: constant early_entrant column leaked into features")

        # 6. temporal — NCAA season must equal draft year, never later
        s = feats.dropna(subset=["ncaa_season"])
        check((s.ncaa_season == s.draft_year).all(),
              f"{label}: ncaa_season != draft_year on "
              f"{int((s.ncaa_season != s.draft_year).sum())} rows")
        check(s.ncaa_season.max() <= s.draft_year.max(),
              f"{label}: future NCAA season present")
        check(set(feats.draft_year) <= set(years),
              f"{label}: draft years outside partition: "
              f"{sorted(set(feats.draft_year) - set(years))}")

        # 7. impossible shooting / counting totals
        d = feats.dropna(subset=["field_goals_attempted"])
        for made, att in [("field_goals_made", "field_goals_attempted"),
                          ("three_points_made", "three_points_attempted"),
                          ("free_throws_made", "free_throws_attempted"),
                          ("two_points_made", "two_points_attempted")]:
            check((d[made] <= d[att]).all(),
                  f"{label}: {made} > {att} on {int((d[made] > d[att]).sum())} rows")
        num = [c for c in ("points", "minutes", "games_played", "assists",
                           "turnovers", "steals", "blocks", "total_rebounds",
                           "two_points_made", "two_points_attempted") if c in d]
        for c in num:
            check((d[c] >= 0).all(),
                  f"{label}: negative values in {c} "
                  f"({int((d[c] < 0).sum())} rows)")
        check((d.games_started <= d.games_played).all(),
              f"{label}: games_started > games_played")

        # 8. identifiers
        ids = feats.hoopr_athlete_id.dropna()
        check((ids > 0).all(), f"{label}: non-positive hoopr_athlete_id present")
        check(not ids.duplicated().any(),
              f"{label}: same hoopr_athlete_id mapped to >1 prospect "
              f"({int(ids.duplicated().sum())} cases)", hard=False)

        # 9. targets minimal and well-formed
        check(set(tgt.columns) == {"canonical_prospect_id", "draft_year",
                                   "drafted", "pick", "round"},
              f"{label}: unexpected target columns: {sorted(tgt.columns)}")
        drafted = tgt[tgt.drafted == 1]
        check(drafted["pick"].notna().all(),
              f"{label}: drafted rows with null pick")
        check(tgt[tgt.drafted == 0]["pick"].isna().all(),
              f"{label}: undrafted rows carrying a pick")
        if len(drafted):
            check(drafted["pick"].between(1, 60).all(),
                  f"{label}: pick outside 1-60", hard=False)

        all_ids[label] = fk

    # 10. no partition overlap — 2026 must never mix with development
    dev, hold = all_ids.get("2014_2025", set()), all_ids.get("2026", set())
    rob = all_ids.get("2011_2013", set())
    check(not (dev & hold), f"2026 holdout overlaps development: {len(dev & hold)}")
    check(not (dev & rob), f"robustness overlaps development: {len(dev & rob)}")
    check((OUT / "features_2026.parquet").exists()
          and (OUT / "features_2014_2025.parquet").exists(),
          "development and holdout must be physically separate files")

    # 11. quality report present
    check((OUT / "quality_report.json").exists(), "quality_report.json missing")
    if (OUT / "quality_report.json").exists():
        rep = json.loads((OUT / "quality_report.json").read_text())
        check(not rep.get("gate_failures"),
              f"build reported gate failures: {rep.get('gate_failures')}")

    rule("VALIDATION RESULT")
    print(f"  hard failures: {len(FAIL)}")
    print(f"  warnings     : {len(WARN)}")
    for m in FAIL:
        print(f"   FAIL {m}")
    for m in WARN:
        print(f"   WARN {m}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
