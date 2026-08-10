"""Build the model-ready prospect dataset, and load it back with the 2026
holdout firewall built in.

Raw sources -> identity resolution -> season aggregation -> one row per
prospect -> engineered feature layer (`features.basketball`). Population gates
and leakage audits run on every build; a failure returns a non-zero status
rather than writing a quietly wrong dataset.

`load_development` and `load_stage_b` are the ONLY approved ways to obtain
labelled data for modelling. Both assert that 2026 is absent, so a phase
cannot accidentally train on the holdout by importing the wrong parquet file.
The 2026 partition is deliberately NOT loadable from this module.
"""

import json

import pandas as pd

from features.basketball import BOX_SUMS, feature_columns
from data.matching import load_overrides, match_prospects, season_index
from paths import INTERIM, interim
from data.population import COVID_YEARS, EXPECTED, load_population, load_targets
from validation import (DENIED, DENIED_SUBSTR, DENY_EXACT, DENY_SUBSTRING,
                        HOLDOUT_YEAR, SUSPICIOUS, SUSPICIOUS_ALLOWED,
                        assert_no_holdout)

DATASET = INTERIM / "dataset"
FEATURES = INTERIM / "features"

PARTITIONS = {"2011_2013": list(range(2011, 2014)),
              "2014_2025": list(range(2014, 2026)),
              "2026": [2026]}


# --------------------------------------------------------------- audits
def leakage_audit(feats, label, report):
    """Columns that must never have been written, plus a review list.

    SUSPICIOUS is deliberately noisy — it flags anything name-matching "draft",
    "pick", "rank" etc. so a new column has to be consciously reviewed rather
    than slipping in because it looked harmless.
    """
    cols = list(feats.columns)
    hard = [c for c in cols if c.lower() in DENY_EXACT
            or any(s in c.lower() for s in DENY_SUBSTRING)]
    susp = [c for c in cols
            if any(s in c.lower() for s in SUSPICIOUS) and c not in SUSPICIOUS_ALLOWED
            and c not in hard]
    report[label] = dict(n_columns=len(cols), denied=hard,
                         suspicious_for_review=susp)
    return hard


def temporal_audit(feats, years, label, report):
    """Every row's NCAA season must equal its draft year, and no draft year may
    fall outside the partition window."""
    bad = feats[feats.ncaa_season.notna()
                & (feats.ncaa_season != feats.draft_year)]
    off_window = sorted(set(feats.draft_year) - set(years))
    report[label] = dict(rows=len(feats),
                         season_mismatch_rows=int(len(bad)),
                         draft_years=sorted(map(int, feats.draft_year.unique())),
                         unexpected_years=off_window)
    return len(bad) == 0 and not off_window


def missingness(feats, cols):
    out = {}
    for c in cols:
        if c not in feats.columns:
            continue
        n_missing = int(feats[c].isna().sum())
        out[c] = dict(missing=n_missing,
                      missing_pct=round(100 * n_missing / max(1, len(feats)), 2))
    return out


def coverage_by_outcome(feats, tgt, cols):
    """2014-2025 ONLY. Detects missingness that correlates with the target.

    A column whose AVAILABILITY differs between drafted and undrafted prospects
    is a leakage channel regardless of its values — this is how the DOB and
    position-label leaks were both found.
    """
    m = feats.merge(tgt[["canonical_prospect_id", "drafted"]],
                    on="canonical_prospect_id", how="inner")
    out = {}
    for c in cols:
        if c not in m.columns:
            continue
        d = 100 * m.loc[m.drafted == 1, c].notna().mean()
        u = 100 * m.loc[m.drafted == 0, c].notna().mean()
        out[c] = dict(drafted_coverage_pct=round(float(d), 2),
                      undrafted_coverage_pct=round(float(u), 2),
                      gap_pp=round(float(d - u), 2))
    return out


# ---------------------------------------------------------------- build
def build_year(year, overrides, stats):
    """One draft year: population, matching, aggregation, targets."""
    from features.basketball import aggregate_box, physical
    from features.shot_profile import aggregate_shots

    pop = load_population(year)
    idx = season_index(year)
    pop = match_prospects(pop, idx, overrides)

    matched_ids = set(pop.hoopr_athlete_id.dropna().astype("int64"))
    box_agg, dupes, box_rows = aggregate_box(year, matched_ids)
    shots_agg = aggregate_shots(year, matched_ids)
    phys = physical(year, matched_ids)

    # Identity/context only. position/class from the population are NOT carried
    # into the feature file — they are outcome-contaminated. They stay
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
    out = out if out is not None else interim("dataset")
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


# --------------------------------------------------------------- loading
def _labelled(features_file, targets_file):
    f = pd.read_parquet(FEATURES / features_file)
    t = pd.read_parquet(DATASET / targets_file)
    m = f.merge(t[["canonical_prospect_id", "drafted", "pick"]],
                on="canonical_prospect_id", how="inner")
    assert HOLDOUT_YEAR not in set(m.draft_year), "HOLDOUT GUARD: 2026 present"
    return m


def load_development():
    """Engineered features joined to development targets, 2014-2025. 887
    prospects."""
    return _labelled("features_2014_2025.parquet", "targets_2014_2025.parquet")


def load_robustness():
    """2011-2013. Sensitivity analysis only — never the default training set,
    and never permitted to influence a selection decision."""
    return _labelled("features_2011_2013.parquet", "targets_2011_2013.parquet")


def load_draft_order(robustness=False):
    """Drafted early entrants only — the Draft Order population (431 in
    2014-2025).

    Undrafted prospects are REMOVED, never relabelled. Assigning them a
    sentinel pick (61, 100, 999) would invent data and distort the loss
    surface, so a row without a real pick cannot reach Draft Order.
    """
    df = load_robustness() if robustness else load_development()
    d = df[df.drafted == 1].copy()
    assert d.pick.notna().all(), "a drafted prospect has no pick — refusing to invent one"
    assert_no_holdout(d, "draft order")
    d["pick"] = d["pick"].astype(int)
    return d.reset_index(drop=True)


# -------------------------------------------------------------- validation
def validate():
    """Hard-fails on population, leakage, integrity or holdout-bleed errors in
    either the built dataset or the engineered feature layer.

      ./.venv/bin/python scripts/validate.py
    """
    import numpy as np

    from validation import Guard

    g = Guard()

    if not (DATASET / "features_2014_2025.parquet").exists():
        g.check(False, "dataset outputs not found — run scripts/build.py")
        return g.report()

    # -------------------------------------------------- built dataset (raw)
    all_ids = {}
    for label, years in PARTITIONS.items():
        feats = pd.read_parquet(DATASET / f"features_{label}.parquet")
        tgt = pd.read_parquet(DATASET / f"targets_{label}.parquet")

        exp = EXPECTED.get(label)
        if exp:
            n, nd = len(feats), int(tgt.drafted.sum())
            nu = int((tgt.drafted == 0).sum())
            g.check(n == exp[0], f"{label}: expected {exp[0]} rows, got {n}")
            if exp[1] is not None:
                g.check(nd == exp[1], f"{label}: expected {exp[1]} drafted, got {nd}")
                g.check(nu == exp[2], f"{label}: expected {exp[2]} undrafted, got {nu}")

        g.check(not feats.canonical_prospect_id.duplicated().any(),
                f"{label}: duplicate canonical_prospect_id in features")
        g.check(not tgt.canonical_prospect_id.duplicated().any(),
                f"{label}: duplicate canonical_prospect_id in targets")
        fk, tk = set(feats.canonical_prospect_id), set(tgt.canonical_prospect_id)
        g.check(fk == tk, f"{label}: feature/target keys differ "
                          f"(features-only={len(fk-tk)}, targets-only={len(tk-fk)})")

        cols = [c.lower() for c in feats.columns]
        denied = [c for c in cols if c in DENY_EXACT
                  or any(s in c for s in DENY_SUBSTRING)]
        g.check(not denied, f"{label}: PROHIBITED columns in feature file: {denied}")
        g.check("early_entrant" not in cols,
                f"{label}: constant early_entrant column leaked into features")

        s = feats.dropna(subset=["ncaa_season"])
        g.check((s.ncaa_season == s.draft_year).all(),
                f"{label}: ncaa_season != draft_year on "
                f"{int((s.ncaa_season != s.draft_year).sum())} rows")
        g.check(set(feats.draft_year) <= set(years),
                f"{label}: draft years outside partition: "
                f"{sorted(set(feats.draft_year) - set(years))}")

        d = feats.dropna(subset=["field_goals_attempted"])
        for made, att in [("field_goals_made", "field_goals_attempted"),
                          ("three_points_made", "three_points_attempted"),
                          ("free_throws_made", "free_throws_attempted"),
                          ("two_points_made", "two_points_attempted")]:
            g.check((d[made] <= d[att]).all(),
                    f"{label}: {made} > {att} on {int((d[made] > d[att]).sum())} rows")

        ids = feats.hoopr_athlete_id.dropna()
        g.check((ids > 0).all(), f"{label}: non-positive hoopr_athlete_id present")

        drafted = tgt[tgt.drafted == 1]
        g.check(drafted["pick"].notna().all(),
                f"{label}: drafted rows with null pick")
        g.check(tgt[tgt.drafted == 0]["pick"].isna().all(),
                f"{label}: undrafted rows carrying a pick")

        all_ids[label] = fk

    dev, hold = all_ids.get("2014_2025", set()), all_ids.get("2026", set())
    rob = all_ids.get("2011_2013", set())
    g.check(not (dev & hold), f"2026 holdout overlaps development: {len(dev & hold)}")
    g.check(not (dev & rob), f"robustness overlaps development: {len(dev & rob)}")
    print(f"  1. built dataset: population gates, leakage and temporal "
          f"integrity hold across all {len(PARTITIONS)} partitions")

    # ---------------------------------------------- engineered feature layer
    if not (FEATURES / "features_2014_2025.parquet").exists():
        g.check(False, "feature layer missing — run scripts/build.py")
        return g.report()

    forbidden = {"drafted", "pick", "round", "drafting_team",
                 "position_from_population", "class_from_population",
                 "match_method", "match_confidence",
                 "date_of_birth", "age", "current_age", "dob"}
    forbidden_substr = ("jump_shot", "nba_", "mock", "consensus", "analyst")

    frames = {}
    for label in EXPECTED:
        f = pd.read_parquet(FEATURES / f"features_{label}.parquet")
        frames[label] = f
        cols = {c.lower() for c in f.columns}
        bad = cols & forbidden
        g.check(not bad, f"{label}: forbidden columns present: {sorted(bad)}")
        sub = [c for c in cols if any(s in c for s in forbidden_substr)]
        g.check(not sub, f"{label}: forbidden-substring columns: {sub}")

        feats = feature_columns(f)
        num = f[feats]
        infs = {c: int(np.isinf(num[c].dropna()).sum()) for c in feats
                if np.isinf(num[c].dropna()).any()}
        g.check(not infs, f"{label}: infinities in {infs}")

        m0 = pd.read_parquet(DATASET / f"features_{label}.parquet")
        g.check(set(f.canonical_prospect_id) == set(m0.canonical_prospect_id),
                f"{label}: prospect set differs from the built dataset "
                f"(lost {len(set(m0.canonical_prospect_id) - set(f.canonical_prospect_id))})")

    dev_ids = set(frames["2014_2025"].canonical_prospect_id)
    hold_ids = set(frames["2026"].canonical_prospect_id)
    g.check(not (dev_ids & hold_ids), "2026 holdout overlaps development")

    unmatched = int(frames["2014_2025"].hoopr_athlete_id.isna().sum())
    g.check(unmatched >= 8, f"unresolved prospects lost (found {unmatched}, expected >=8)")
    print(f"  2. feature layer: {len(EXPECTED)} partitions clean, "
          f"{unmatched} unresolved prospects retained")

    return g.report()
