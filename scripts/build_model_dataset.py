"""ML-0 — build the model-ready prospect dataset (features and targets, separated).

Population: FINAL NCAA EARLY ENTRANTS ONLY (DEC-049). Seniors known only because
they were drafted are excluded — their membership carries post-draft information.

Outputs (all git-ignored) under data/interim/ml0/:
    features_<partition>.parquet   pre-draft primitives only
    targets_<partition>.parquet    outcomes only, physically separate
    identity_crosswalk.parquet     prospect -> hoopR athlete_id with match method
    quality_report.json            counts, coverage, missingness, audits

This script computes PRIMITIVES ONLY. No percentages, rates, per-40, per-100,
scaling, normalisation, imputation, or scores — those belong to later phases
(ML_SPEC §26, §27).

  ./.venv/bin/python scripts/build_model_dataset.py
  ./.venv/bin/python scripts/build_model_dataset.py --years 2014-2025
"""

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dlcommon import RAW, ROOT, normalize_name  # noqa: E402

OUT = ROOT / "data" / "interim" / "ml0"
MBB = RAW / "hoopr_mbb"
POP_DIR, TGT_DIR = RAW / "draft_population", RAW / "draft_targets"
OVERRIDES = ROOT / "config" / "identity_overrides.csv"

PARTITIONS = {
    "2011_2013": list(range(2011, 2014)),
    "2014_2025": list(range(2014, 2026)),
    "2026": [2026],
}
# Authoritative population gates. Corrected in ML-0.1 after the NCAA
# classification fix (DEC-063); the pre-correction values (829/403/426 and
# 119/79/40) were produced by a defective parser and are NOT authoritative.
EXPECTED = {"2014_2025": (887, 431, 456), "2026": (26, None, None),
            "2011_2013": (125, 85, 40)}
COVID_YEARS = {2021, 2022}

# Columns that must NEVER appear in a feature file (ML_SPEC §8.1).
DENY_EXACT = {
    "drafted", "pick", "round", "drafting_team", "early_entrant",
    "population_source", "date_of_birth", "age", "current_age", "dob",
    "dob_missing", "draft_year_pick", "nba_player_id", "nba_athlete_id",
    "mock_rank", "consensus_rank", "analyst_rank", "green_room",
    "draft_selection", "draft_round",
}
DENY_SUBSTRING = ("nba_", "_nba", "mock", "consensus", "analyst", "greenroom",
                  "postdraft", "post_draft", "outcome")
SUSPICIOUS = ("draft", "nba", "pick", "round", "rank", "future", "outcome", "target")
# Reviewed and allowed despite matching SUSPICIOUS: they are identity/context only.
SUSPICIOUS_ALLOWED = {"draft_year"}

BOX_SUMS = {
    "minutes": "minutes", "points": "points",
    "field_goals_made": "field_goals_made",
    "field_goals_attempted": "field_goals_attempted",
    "three_points_made": "three_point_field_goals_made",
    "three_points_attempted": "three_point_field_goals_attempted",
    "free_throws_made": "free_throws_made",
    "free_throws_attempted": "free_throws_attempted",
    "offensive_rebounds": "offensive_rebounds",
    "defensive_rebounds": "defensive_rebounds",
    "total_rebounds": "rebounds",
    "assists": "assists", "turnovers": "turnovers",
    "steals": "steals", "blocks": "blocks", "personal_fouls": "fouls",
}


def log(msg=""):
    print(msg, flush=True)


def rule(t):
    log(f"\n{'=' * 78}\n{t}\n{'=' * 78}")


def to_int_id(s):
    """Dtype-safe athlete_id -> Int64 (player_core int64, box/shots float64)."""
    return pd.to_numeric(s, errors="coerce").astype("Int64")


def match_key(s):
    """Matching-only name key. Never replaces `normalized_name`, which is the
    canonical identity written by acquire_draft_population.py.

    Two deterministic corrections over normalize_name, both general rules and
    not player-specific:
      1. Suffixes (jr/sr/ii/iii/iv/v) are stripped ONLY at the end. normalize_name
         strips them anywhere, so a leading initial "V." in "V. J. Edgecombe" is
         wrongly removed as the Roman numeral V.
      2. Leading single-letter tokens are merged: Wikipedia writes "T. J. Warren",
         ESPN writes "TJ Warren".
    """
    s = str(s).lower()
    for a, b in (("ø", "o"), ("æ", "ae"), ("å", "a"), ("ß", "ss"), ("ł", "l"),
                 ("đ", "d"), ("ð", "d"), ("þ", "th"), ("ı", "i")):
        s = s.replace(a, b)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    toks = re.sub(r"[^a-z ]", "", s).split()
    while toks and toks[-1] in {"jr", "sr", "ii", "iii", "iv", "v"}:
        toks.pop()
    lead, i = [], 0
    while i < len(toks) - 1 and len(toks[i]) == 1:
        lead.append(toks[i])
        i += 1
    if lead:
        toks = ["".join(lead)] + toks[i:]
    return " ".join(toks)


def norm_school(s):
    if not isinstance(s, str):
        return ""
    s = s.lower().replace("’", "'")
    for junk in (" men's basketball", " basketball"):   # strip BEFORE apostrophes
        s = s.replace(junk, "")
    s = s.replace("&", " and ").replace("'", "")
    s = s.replace("st.", "state").replace("–", "-").replace("—", "-")
    return " ".join(s.split())


def load_overrides():
    if not OVERRIDES.exists():
        return {}
    df = pd.read_csv(OVERRIDES)
    return {(int(r.draft_year), str(r.normalized_name)): int(r.athlete_id)
            for r in df.itertuples() if not pd.isna(r.athlete_id)}


# ---------------------------------------------------------------- population
def load_population(year):
    """Final NCAA early entrants only — the approved ML sampling frame."""
    pop = pd.read_csv(POP_DIR / f"draft_population_{year}.csv")
    pop = pop[pop.early_entrant.astype(str) == "True"].copy()
    pop["draft_year"] = year
    pop["canonical_prospect_id"] = (
        pop.draft_year.astype(str) + "-" + pop.normalized_name.str.replace(" ", "_"))
    return pop.reset_index(drop=True)


def load_targets(year, pop):
    tgt = pd.read_csv(TGT_DIR / f"draft_targets_{year}.csv")
    tgt = tgt[tgt.normalized_name.isin(set(pop.normalized_name))].copy()
    tgt["draft_year"] = year
    tgt["canonical_prospect_id"] = (
        tgt.draft_year.astype(str) + "-" + tgt.normalized_name.str.replace(" ", "_"))
    tgt["drafted"] = tgt.drafted.astype(str).eq("True").astype(int)
    tgt["pick"] = pd.to_numeric(tgt["pick"], errors="coerce").astype("Int64")
    tgt["round"] = pd.to_numeric(tgt["round"], errors="coerce").astype("Int64")
    return tgt[["canonical_prospect_id", "draft_year", "drafted", "pick", "round"]]


# ------------------------------------------------------------------ hoopR
def season_index(year):
    """Per-season athlete index from player_box (+ player_core for names)."""
    box = pd.read_parquet(
        MBB / "player_box" / f"player_box_{year}.parquet",
        columns=["athlete_id", "athlete_display_name", "team_id", "team_location",
                 "team_display_name", "did_not_play", "game_id"])
    box["athlete_id"] = to_int_id(box.athlete_id)
    box = box[box.athlete_id.notna()]
    idx = (box.groupby("athlete_id")
              .agg(name=("athlete_display_name", "first"),
                   schools=("team_location", lambda s: sorted(set(s.dropna()))),
                   n_games_rows=("game_id", "size"))
              .reset_index())
    idx["match_key"] = idx.name.map(match_key)
    idx["schools_norm"] = idx.schools.map(lambda xs: {norm_school(x) for x in xs})
    return idx


def surname_school_prefix(prospect_key, college, idx):
    """Deterministic fallback: same surname, same school, and one first name is a
    prefix of the other (e.g. "Simisola Shittu" vs "Simi Shittu"). Requires a
    UNIQUE candidate. General rule, not a player-specific exception.
    """
    toks = prospect_key.split()
    if len(toks) < 2:
        return None
    first, surname = toks[0], toks[-1]
    school = norm_school(college)
    if not school:
        return None
    hits = []
    for r in idx.itertuples():
        kt = r.match_key.split()
        if len(kt) < 2 or kt[-1] != surname:
            continue
        if not any(school == s or school in s or s in school for s in r.schools_norm):
            continue
        f2 = kt[0]
        if len(first) >= 3 and len(f2) >= 3 and (f2.startswith(first)
                                                 or first.startswith(f2)):
            hits.append(r)
    return int(hits[0].athlete_id) if len(hits) == 1 else None


def match_prospects(pop, idx, overrides):
    """Deterministic name+school matching. Never forces an ambiguous match."""
    by_name = {}
    for r in idx.itertuples():
        by_name.setdefault(r.match_key, []).append(r)

    out = []
    for p in pop.itertuples():
        key = (int(p.draft_year), str(p.normalized_name))
        if key in overrides:
            out.append((overrides[key], "OVERRIDE", "high"))
            continue
        pk = match_key(p.player_name)
        cands = by_name.get(pk, [])
        if not cands:
            hit = surname_school_prefix(pk, p.college, idx)
            out.append((hit, "SURNAME_SCHOOL_PREFIX", "high") if hit is not None
                       else (pd.NA, "UNMATCHED", "none"))
            continue
        if len(cands) == 1:
            out.append((int(cands[0].athlete_id), "NORMALIZED_EXACT", "high"))
            continue
        school = norm_school(p.college)
        hits = [c for c in cands
                if school and any(school == s or school in s or s in school
                                  for s in c.schools_norm)]
        if len(hits) == 1:
            out.append((int(hits[0].athlete_id), "DISAMBIGUATED", "high"))
        else:
            out.append((pd.NA, "AMBIGUOUS", "none"))
    res = pd.DataFrame(out, columns=["hoopr_athlete_id", "match_method",
                                     "match_confidence"], index=pop.index)
    res["hoopr_athlete_id"] = res.hoopr_athlete_id.astype("Int64")
    return pd.concat([pop, res], axis=1)


# ------------------------------------------------------------- aggregation
def aggregate_box_frame(box, year):
    """Pure season-aggregation logic (kept separate so it is unit-testable).

    Transfer policy: a prospect's draft-year record is their TOTAL production
    across every NCAA team played for that season — one row per prospect, with
    n_teams retained as metadata. Exact duplicate (athlete_id, game_id) rows are
    dropped before summing so statistics are never double counted.
    """
    before = len(box)
    box = box.drop_duplicates(subset=["athlete_id", "game_id"], keep="first")
    dupes_removed = before - len(box)

    box["_dnp"] = box.did_not_play.fillna(False).astype(bool)
    played = box[~box._dnp].copy()
    for src in BOX_SUMS.values():
        played[src] = pd.to_numeric(played[src], errors="coerce")

    agg = played.groupby("athlete_id").agg(
        **{out: (src, "sum") for out, src in BOX_SUMS.items()})
    agg["games_played"] = played.groupby("athlete_id").size()
    agg["games_started"] = (played.assign(_s=played.starter.fillna(False).astype(bool))
                            .groupby("athlete_id")._s.sum())
    agg["n_teams"] = played.groupby("athlete_id").team_id.nunique()
    agg["primary_school"] = (played.sort_values("game_date")
                             .groupby("athlete_id").team_location.last())
    agg["ncaa_season"] = year
    return agg.reset_index(), dupes_removed, before


def aggregate_box(year, ids):
    box = pd.read_parquet(MBB / "player_box" / f"player_box_{year}.parquet")
    box["athlete_id"] = to_int_id(box.athlete_id)
    box = box[box.athlete_id.isin(ids)].copy()
    return aggregate_box_frame(box, year)


def aggregate_shots_frame(sh):
    """Pure shot-aggregation logic (unit-testable). Uses type_text, score_value
    and assist linkage only — never the sentinel-contaminated coordinates."""
    # shots contains ONLY made free throws -> exclude entirely (DATA.md §22.3)
    sh = sh[~sh.type_text.astype(str).str.contains("FreeThrow", na=False)]
    sh["made"] = sh.scoring_play.fillna(False).astype(bool)
    sh["assisted"] = sh.athlete_id_2.notna()

    cat = {"JumpShot": "jump_shot", "LayUpShot": "layup",
           "DunkShot": "dunk", "TipShot": "tip"}
    sh["cat"] = sh.type_text.map(cat)

    # Vectorised indicator columns, then a single grouped sum. score_value
    # encodes the shot's point value for makes AND misses, so 3PT is
    # identifiable without touching the contaminated coordinates.
    is3 = sh.score_value == 3
    ind = pd.DataFrame({
        "shot_records": 1,
        "fg_attempts_shotfile": 1,
        "fg_makes_shotfile": sh.made,
        "three_point_shot_attempts": is3,
        "three_point_shot_makes": is3 & sh.made,
        "assisted_made_field_goals": sh.made & sh.assisted,
        "unassisted_made_field_goals": sh.made & ~sh.assisted,
    }, index=sh.index)
    for c in cat.values():
        inc = sh.cat == c
        ind[f"{c}_attempts"] = inc
        ind[f"{c}_makes"] = inc & sh.made
        if c in ("layup", "dunk"):
            ind[f"assisted_{c}_makes"] = inc & sh.made & sh.assisted
            ind[f"unassisted_{c}_makes"] = inc & sh.made & ~sh.assisted

    out = ind.astype("int64").groupby(sh.athlete_id_1).sum()
    return out.rename_axis("athlete_id").reset_index()


def aggregate_shots(year, ids):
    sh = pd.read_parquet(
        MBB / "shots" / f"shots_{year}.parquet",
        columns=["athlete_id_1", "athlete_id_2", "type_text", "scoring_play",
                 "score_value"])
    sh["athlete_id_1"] = to_int_id(sh.athlete_id_1)
    sh = sh[sh.athlete_id_1.isin(ids)].copy()
    return aggregate_shots_frame(sh)


def physical(year, ids):
    core = pd.read_parquet(MBB / "player_core" / f"player_core_{year}.parquet")
    core["athlete_id"] = to_int_id(core.athlete_id)
    core = core[core.athlete_id.isin(ids)]
    keep = core[["athlete_id", "position_abbreviation", "height", "weight",
                 "experience_years"]].copy()
    return keep.rename(columns={"position_abbreviation": "hoopr_position"})


# ---------------------------------------------------------------- assembly
def build_year(year, overrides, stats):
    pop = load_population(year)
    idx = season_index(year)
    pop = match_prospects(pop, idx, overrides)

    matched_ids = set(pop.hoopr_athlete_id.dropna().astype("int64"))
    box_agg, dupes, box_rows = aggregate_box(year, matched_ids)
    shots_agg = aggregate_shots(year, matched_ids)
    phys = physical(year, matched_ids)

    feats = (pop[["canonical_prospect_id", "draft_year", "player_name",
                  "normalized_name", "college", "position", "class",
                  "wikipedia_title", "hoopr_athlete_id", "match_method",
                  "match_confidence"]]
             .rename(columns={"position": "position_from_population",
                              "class": "class_from_population"}))
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
    return feats, tgt


# ----------------------------------------------------------------- audits
def leakage_audit(feats, label, report):
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
    """2014-2025 ONLY. Detects missingness that correlates with the target."""
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", default=None,
                    help="restrict build, e.g. 2014-2025 (default: all partitions)")
    a = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    overrides = load_overrides()
    parts = PARTITIONS
    if a.years:
        lo, hi = (a.years.split("-") + [a.years])[:2]
        want = set(range(int(lo), int(hi) + 1))
        parts = {k: [y for y in v if y in want] for k, v in PARTITIONS.items()}
        parts = {k: v for k, v in parts.items() if v}

    report = {"partitions": {}, "per_year": {}, "leakage": {}, "temporal": {},
              "missingness": {}, "coverage_by_outcome": {}, "gates": {}}
    stats, crosswalks, gate_failures = {}, [], []

    for label, years in parts.items():
        rule(f"PARTITION {label}  years={years[0]}-{years[-1]}")
        fs, ts = [], []
        for y in years:
            f, t = build_year(y, overrides, stats)
            fs.append(f)
            ts.append(t)
            s = stats[y]
            log(f"  {y}: prospects={s['prospects']:<4} matched={s['matched']:<4} "
                f"unmatched={s['unmatched']:<3} ambig={s['ambiguous']:<3} "
                f"box={s['with_box']:<4} shots={s['with_shots']:<4} "
                f"multi_team={s['multi_team']:<3} dupes_removed={s['box_dupe_rows_removed']}")
        feats = pd.concat(fs, ignore_index=True)
        tgt = pd.concat(ts, ignore_index=True)

        # ---- population gates
        exp = EXPECTED.get(label)
        n, nd, nu = len(feats), int(tgt.drafted.sum()), int((tgt.drafted == 0).sum())
        if exp:
            ok = (n == exp[0] and (exp[1] is None or nd == exp[1])
                  and (exp[2] is None or nu == exp[2]))
            report["gates"][label] = dict(expected=exp, observed=[n, nd, nu], pass_=ok)
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
            report["coverage_by_outcome"][label] = coverage_by_outcome(feats, tgt, prim)

        report["partitions"][label] = dict(
            rows=n, drafted=nd, undrafted=nu,
            matched=int(feats.hoopr_athlete_id.notna().sum()),
            match_rate_pct=round(100 * feats.hoopr_athlete_id.notna().mean(), 2))

        feats.to_parquet(OUT / f"features_{label}.parquet", index=False)
        tgt.to_parquet(OUT / f"targets_{label}.parquet", index=False)
        crosswalks.append(feats[["canonical_prospect_id", "draft_year",
                                 "player_name", "normalized_name", "college",
                                 "wikipedia_title", "hoopr_athlete_id",
                                 "match_method", "match_confidence"]])
        log(f"  wrote features_{label}.parquet ({n} rows, {len(feats.columns)} cols)"
            f" and targets_{label}.parquet")

    pd.concat(crosswalks, ignore_index=True).to_parquet(
        OUT / "identity_crosswalk.parquet", index=False)
    report["per_year"] = {str(k): v for k, v in sorted(stats.items())}
    report["gate_failures"] = gate_failures
    (OUT / "quality_report.json").write_text(json.dumps(report, indent=2, default=str))

    rule("ML-0 BUILD RESULT")
    for k, v in report["partitions"].items():
        log(f"  {k:<10} rows={v['rows']:<5} drafted={v['drafted']:<4} "
            f"undrafted={v['undrafted']:<4} match={v['match_rate_pct']}%")
    log(f"\n  gate failures: {len(gate_failures)}")
    for g in gate_failures:
        log(f"    FAIL {g}")
    return 1 if gate_failures else 0


if __name__ == "__main__":
    sys.exit(main())
