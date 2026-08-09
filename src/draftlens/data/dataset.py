"""Build the ML-0 model-ready prospect dataset.

Raw sources -> identity resolution -> season aggregation -> one row per prospect.

Population gates and leakage audits run on every build; a failure returns a
non-zero status rather than writing a quietly wrong dataset.
"""

import json

import pandas as pd

from draftlens.data.identity.matching import (load_overrides, match_prospects,
                                              season_index)
from draftlens.data.population import (COVID_YEARS, EXPECTED, load_population,
                                       load_targets)
from draftlens.data.validation.audits import (coverage_by_outcome, leakage_audit,
                                              missingness, temporal_audit)
from draftlens.features.boxscore import BOX_SUMS, aggregate_box
from draftlens.features.physical import physical
from draftlens.features.shot_profile import aggregate_shots
from draftlens.paths import interim

PARTITIONS = {"2011_2013": list(range(2011, 2014)),
              "2014_2025": list(range(2014, 2026)),
              "2026": [2026]}


def build_year(year, overrides, stats):
    """One draft year: population, matching, aggregation, targets."""
    pop = load_population(year)
    idx = season_index(year)
    pop = match_prospects(pop, idx, overrides)

    matched_ids = set(pop.hoopr_athlete_id.dropna().astype("int64"))
    box_agg, dupes, box_rows = aggregate_box(year, matched_ids)
    shots_agg = aggregate_shots(year, matched_ids)
    phys = physical(year, matched_ids)

    # Identity/context only. position/class from the population are NOT carried
    # into the feature file (DEC-065) — they are outcome-contaminated. They stay
    # available in data/raw/draft_population/ and identity_crosswalk.parquet.
    feats = (pop[["canonical_prospect_id", "draft_year", "player_name",
                  "normalized_name", "college", "wikipedia_title",
                  "hoopr_athlete_id"]])
    feats = (feats.merge(box_agg, left_on="hoopr_athlete_id",
                         right_on="athlete_id", how="left")
                  .merge(shots_agg, left_on="hoopr_athlete_id",
                         right_on="athlete_id", how="left", suffixes=("", "_sh"))
                  .merge(phys, left_on="hoopr_athlete_id",
                         right_on="athlete_id", how="left", suffixes=("", "_ph")))
    feats = feats.drop(columns=[c for c in feats.columns
                                if c.startswith("athlete_id")])

    # identity-preserving arithmetic primitives only
    feats["two_points_made"] = feats.field_goals_made - feats.three_points_made
    feats["two_points_attempted"] = (feats.field_goals_attempted
                                     - feats.three_points_attempted)
    feats["covid_era_flag"] = int(year in COVID_YEARS)      # metadata, not a feature

    cw = pop[["canonical_prospect_id", "draft_year", "player_name",
              "normalized_name", "college", "position", "class",
              "wikipedia_title", "hoopr_athlete_id", "match_method",
              "match_confidence"]].rename(
        columns={"position": "position_from_population",
                 "class": "class_from_population"})

    tgt = load_targets(year, pop)
    stats[year] = dict(
        prospects=len(pop), matched=int(pop.hoopr_athlete_id.notna().sum()),
        unmatched=int((pop.match_method == "UNMATCHED").sum()),
        ambiguous=int((pop.match_method == "AMBIGUOUS").sum()),
        overrides=int((pop.match_method == "OVERRIDE").sum()),
        box_dupe_rows_removed=int(dupes), box_rows_read=int(box_rows),
        with_box=int(feats.games_played.notna().sum()),
        with_shots=int(feats.shot_records.notna().sum()),
        multi_team=int((feats.n_teams > 1).sum()),
        drafted=int(tgt.drafted.sum()), undrafted=int((tgt.drafted == 0).sum()),
        covid_era=int(year in COVID_YEARS))
    return feats, tgt, cw


def build_prospect_dataset(partitions=None, out=None, log=print):
    """Build every partition, run the gates, write parquet + quality report.

    Returns (report, gate_failures).
    """
    out = out if out is not None else interim("ml0")
    parts = partitions if partitions is not None else PARTITIONS
    overrides = load_overrides()

    report = {"partitions": {}, "per_year": {}, "leakage": {}, "temporal": {},
              "missingness": {}, "coverage_by_outcome": {}, "gates": {}}
    stats, crosswalks, gate_failures = {}, [], []

    for label, years in parts.items():
        log(f"\nPARTITION {label}  years={years[0]}-{years[-1]}")
        fs, ts, cws = [], [], []
        for y in years:
            f, t, cw = build_year(y, overrides, stats)
            fs.append(f)
            ts.append(t)
            cws.append(cw)
            s = stats[y]
            log(f"  {y}: prospects={s['prospects']:<4} matched={s['matched']:<4} "
                f"unmatched={s['unmatched']:<3} ambig={s['ambiguous']:<3} "
                f"box={s['with_box']:<4} shots={s['with_shots']:<4} "
                f"multi_team={s['multi_team']:<3} "
                f"dupes_removed={s['box_dupe_rows_removed']}")
        feats = pd.concat(fs, ignore_index=True)
        tgt = pd.concat(ts, ignore_index=True)

        # ---- population gates
        exp = EXPECTED.get(label)
        n, nd, nu = len(feats), int(tgt.drafted.sum()), int((tgt.drafted == 0).sum())
        if exp:
            ok = (n == exp[0] and (exp[1] is None or nd == exp[1])
                  and (exp[2] is None or nu == exp[2]))
            report["gates"][label] = dict(expected=exp, observed=[n, nd, nu],
                                          pass_=ok)
            log(f"\n  GATE {label}: expected {exp} observed ({n}, {nd}, {nu}) "
                f"-> {'PASS' if ok else 'FAIL'}")
            if not ok:
                gate_failures.append(label)

        # ---- audits
        denied = leakage_audit(feats, label, report["leakage"])
        if denied:
            gate_failures.append(f"{label}:leakage:{denied}")
        if not temporal_audit(feats, years, label, report["temporal"]):
            gate_failures.append(f"{label}:temporal")
        if feats.canonical_prospect_id.duplicated().any():
            gate_failures.append(f"{label}:duplicate_prospect_ids")
        if set(feats.canonical_prospect_id) != set(tgt.canonical_prospect_id):
            gate_failures.append(f"{label}:feature_target_key_mismatch")

        prim = [c for c in feats.columns if c in BOX_SUMS or c in
                ("games_played", "games_started", "height", "weight",
                 "hoopr_position", "shot_records", "two_points_made",
                 "three_point_shot_attempts", "experience_years")]
        report["missingness"][label] = missingness(feats, prim)
        if label == "2014_2025":
            report["coverage_by_outcome"][label] = coverage_by_outcome(
                feats, tgt, prim)

        report["partitions"][label] = dict(
            rows=n, drafted=nd, undrafted=nu,
            matched=int(feats.hoopr_athlete_id.notna().sum()),
            match_rate_pct=round(100 * feats.hoopr_athlete_id.notna().mean(), 2))

        feats.to_parquet(out / f"features_{label}.parquet", index=False)
        tgt.to_parquet(out / f"targets_{label}.parquet", index=False)
        crosswalks.append(pd.concat(cws, ignore_index=True))
        log(f"  wrote features_{label}.parquet ({n} rows, "
            f"{len(feats.columns)} cols) and targets_{label}.parquet")

    pd.concat(crosswalks, ignore_index=True).to_parquet(
        out / "identity_crosswalk.parquet", index=False)
    report["per_year"] = {str(k): v for k, v in sorted(stats.items())}
    report["gate_failures"] = gate_failures
    (out / "quality_report.json").write_text(json.dumps(report, indent=2,
                                                        default=str))
    return report, gate_failures
