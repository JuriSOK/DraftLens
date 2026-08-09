"""Deterministic prospect -> hoopR athlete matching.

There is no shared identifier between the Wikipedia population and the hoopR
statistics corpus, so prospects are matched on normalised name plus school.

Two rules govern this module:
  * An ambiguous match is left UNMATCHED. Forcing a match would silently attach
    one player's statistics to another, and DATA.md 9.2 measured that match
    failures concentrate in the undrafted class — so a wrong match is a leakage
    risk, not just an error.
  * Every exception is a general rule or an explicitly reviewed override in
    config/data/identity_overrides.csv. No player-specific branches in code.

Unmatched prospects are RETAINED in the population with null statistics
(DEC-071); they are never dropped, because dropping them would selectively
remove undrafted players and inflate downstream performance.
"""

import pandas as pd

from draftlens.data.identity.normalization import match_key, norm_school
from draftlens.paths import CONFIG_DATA, MBB

OVERRIDES = CONFIG_DATA / "identity_overrides.csv"


def to_int_id(s):
    """Dtype-safe athlete_id -> Int64.

    player_core stores int64 while player_box and shots store float64. Casting
    to string without this produces "5142718" vs "5142718.0" and a silent 0%
    join — the ML-0 22.7 defect.
    """
    return pd.to_numeric(s, errors="coerce").astype("Int64")


def load_overrides(path=OVERRIDES):
    """Reviewed name-variant exceptions: (draft_year, normalized_name) -> athlete_id."""
    if not path.exists():
        return {}
    df = pd.read_csv(path)
    return {(int(r.draft_year), str(r.normalized_name)): int(r.athlete_id)
            for r in df.itertuples() if not pd.isna(r.athlete_id)}


def season_index(year):
    """Per-season athlete index from player_box, with the schools each played for."""
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
    """Fallback: same surname, same school, one first name a prefix of the other
    (e.g. "Simisola Shittu" vs "Simi Shittu"). Requires a UNIQUE candidate."""
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
    """Deterministic name+school matching. Never forces an ambiguous match.

    Returns `pop` with hoopr_athlete_id / match_method / match_confidence added.
    match_method and match_confidence are AUDIT columns and are on the ML deny
    list — they describe how a row entered the frame, which correlates with the
    outcome (DEC-065).
    """
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
