"""Identity resolution: name normalisation and prospect -> hoopR matching.

DraftLens joins Wikipedia (population and draft results) to hoopR (statistics)
on names alone — there is no shared identifier. Three distinct keys exist and
they are NOT interchangeable:

  normalize_name  canonical identity, written once into the raw population CSVs.
                  Frozen: changing it would invalidate every canonical_prospect_id.
  match_key       matching-only key with two documented corrections over
                  normalize_name. Never persisted as identity.
  norm_school     school/program key used to disambiguate same-name players.

Two rules govern the matching itself:
  * An ambiguous match is left UNMATCHED. Forcing a match would silently attach
    one player's statistics to another, and match failures concentrate in the
    undrafted class — so a wrong match is a leakage risk, not just an error.
  * Every exception is a general rule or an explicitly reviewed override in
    config/identity_overrides.csv. No player-specific branches in code.

Unmatched prospects are RETAINED in the population with null statistics; they
are never dropped, because dropping them would selectively remove undrafted
players and inflate downstream performance.

Nothing here reads a draft outcome.
"""

import re
import unicodedata

import pandas as pd

from paths import CONFIG, MBB

OVERRIDES = CONFIG / "identity_overrides.csv"

SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}

# Characters NFKD cannot decompose into ASCII + combining marks.
_TRANSLITERATIONS = (("ø", "o"), ("æ", "ae"), ("å", "a"), ("ß", "ss"),
                     ("ł", "l"), ("đ", "d"), ("ð", "d"), ("þ", "th"), ("ı", "i"))


def normalize_name(s):
    """Casefold, strip accents/suffixes/punctuation. The CANONICAL identity key.

    Known quirk, deliberately not fixed: the suffix rule strips "v" anywhere in
    the string, so "V. J. Edgecombe" loses its leading initial. `match_key`
    compensates for matching purposes. Correcting it here would change every
    `canonical_prospect_id` already written to disk.
    """
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b\.?", "", s)
    return re.sub(r"\s+", " ", re.sub(r"[^a-z ]", "", s)).strip()


def match_key(s):
    """Matching-only name key. Never replaces `normalized_name`.

    Two deterministic corrections over normalize_name, both general rules and
    not player-specific:
      1. Suffixes are stripped ONLY at the end, so a leading initial "V." is
         preserved rather than removed as a Roman numeral.
      2. Leading single-letter tokens are merged: Wikipedia writes "T. J. Warren",
         ESPN writes "TJ Warren".
    """
    s = str(s).lower()
    for a, b in _TRANSLITERATIONS:
        s = s.replace(a, b)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    toks = re.sub(r"[^a-z ]", "", s).split()
    while toks and toks[-1] in SUFFIXES:
        toks.pop()
    lead, i = [], 0
    while i < len(toks) - 1 and len(toks[i]) == 1:
        lead.append(toks[i])
        i += 1
    if lead:
        toks = ["".join(lead)] + toks[i:]
    return " ".join(toks)


def norm_school(s):
    """School key. Program suffixes are stripped BEFORE apostrophes, otherwise
    "Saint Mary's men's basketball" loses the wrong substring."""
    if not isinstance(s, str):
        return ""
    s = s.lower().replace("’", "'")
    for junk in (" men's basketball", " basketball"):
        s = s.replace(junk, "")
    s = s.replace("&", " and ").replace("'", "")
    s = s.replace("st.", "state").replace("–", "-").replace("—", "-")
    return " ".join(s.split())


def to_int_id(s):
    """Dtype-safe athlete_id -> Int64.

    player_core stores int64 while player_box and shots store float64. Casting
    to string without this produces "5142718" vs "5142718.0" and a silent 0%
    join.
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
    outcome.
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
