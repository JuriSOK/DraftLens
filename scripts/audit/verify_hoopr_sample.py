"""Small-sample verification of the hoopR static Parquet data (DATA.md §22).

Read-only audit of four 2026 files already present in data/raw/. Prints schemas,
fill rates, ID coverage and a prospect-matching sample. Writes nothing.

Run: ./.venv/bin/python scripts/verify_hoopr_sample.py
"""

import re
import unicodedata
from pathlib import Path

import pandas as pd

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
MBB = RAW / "hoopR-mbb-data"
NBA = RAW / "hoopR-nba-data"

pd.set_option("display.width", 200)


def rule(title):
    print(f"\n{'=' * 78}\n{title}\n{'=' * 78}")


def fill_table(df, cols=None):
    """Column, dtype, non-null count, null % — no row values printed."""
    cols = cols or df.columns
    rows = []
    for c in cols:
        if c not in df.columns:
            continue
        nn = int(df[c].notna().sum())
        # treat empty strings as missing for object columns
        if df[c].dtype == object:
            nn = int((df[c].notna() & (df[c].astype(str).str.strip() != "")).sum())
        rows.append((c, str(df[c].dtype), nn, round(100 * (1 - nn / len(df)), 2)))
    return pd.DataFrame(rows, columns=["column", "dtype", "non_null", "null_pct"])


def norm_name(s):
    """Casefold, strip accents, drop suffixes and punctuation."""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b\.?", "", s)
    s = re.sub(r"[^a-z ]", "", s)
    return re.sub(r"\s+", " ", s).strip()


# ---------------------------------------------------------------- AUDIT 1
rule("AUDIT 1 — mbb/player_core 2026")
core = pd.read_parquet(MBB / "player_core_2026.parquet")
print(f"rows={len(core):,}  cols={len(core.columns)}")
print(f"columns: {list(core.columns)}")
print("\nfill rates:")
print(fill_table(core).to_string(index=False))

for cand in ["athlete_id", "id", "player_id"]:
    if cand in core.columns:
        print(f"\nunique {cand}: {core[cand].nunique():,}")
        break

print("\n>>> PRE-DRAFT AGE FEASIBILITY")
for c in [x for x in core.columns if "birth" in x.lower() or x.lower() in ("age", "dob")]:
    nn = int(core[c].notna().sum())
    if core[c].dtype == object:
        nn = int((core[c].notna() & (core[c].astype(str).str.strip() != "")).sum())
    print(f"  {c:<28} fill {100 * nn / len(core):6.2f}%  ({nn:,}/{len(core):,})")

# ---------------------------------------------------------------- AUDIT 2
rule("AUDIT 2 — mbb/player_box 2026")
box = pd.read_parquet(MBB / "player_box_2026.parquet")
print(f"rows={len(box):,}  cols={len(box.columns)}")
print(f"columns: {list(box.columns)}")

wanted = {
    "athlete_id": "athlete id", "team_id": "team id",
    "athlete_display_name": "player name",
    "athlete_position_abbreviation": "position",
    "minutes": "minutes", "points": "points",
    "field_goals_made": "FGM", "field_goals_attempted": "FGA",
    "three_point_field_goals_made": "3PM", "three_point_field_goals_attempted": "3PA",
    "free_throws_made": "FTM", "free_throws_attempted": "FTA",
    "assists": "AST", "turnovers": "TOV",
    "offensive_rebounds": "OREB", "defensive_rebounds": "DREB", "rebounds": "REB",
    "steals": "STL", "blocks": "BLK", "fouls": "PF",
    "starter": "starts", "game_id": "game id", "season": "season",
    "did_not_play": "DNP flag", "team_score": "team score",
    "opponent_team_score": "opp score",
}
print("\ncritical field availability:")
for col, label in wanted.items():
    print(f"  {'OK ' if col in box.columns else 'MISS'}  {label:<14} {col}")

missing_pct = ["FG%", "2PM", "2PA", "2P%", "3P%", "FT%", "games"]
print(f"\nnot present as columns (derivable): {missing_pct}")
print(f"team-total columns present in player_box: "
      f"{[c for c in box.columns if 'team_score' in c or 'opponent_team_score' in c]}")

# ---------------------------------------------------------------- AUDIT 3
rule("AUDIT 3 — mbb/shots 2026")
shots = pd.read_parquet(MBB / "shots_2026.parquet")
print(f"rows={len(shots):,}  cols={len(shots.columns)}")
print(f"columns: {list(shots.columns)}")
print("\nfill rates:")
print(fill_table(shots).to_string(index=False))

for c in shots.columns:
    lc = c.lower()
    if any(k in lc for k in ("type", "text", "desc")) and shots[c].dtype == object:
        u = shots[c].dropna().unique()
        print(f"\n{c}: {len(u)} distinct values")
        print(f"  most common: {shots[c].value_counts().head(12).to_dict()}")
        break

for c in ["shot_desc", "type_text", "text"]:
    if c in shots.columns:
        print(f"\nsample '{c}' strings (5): {list(shots[c].dropna().unique()[:5])}")
        break

# ---------------------------------------------------------------- AUDIT 6
rule("AUDIT 6 — size, duplicates, transfers")
for name, df in [("player_core", core), ("player_box", box), ("shots", shots)]:
    aid = "athlete_id" if "athlete_id" in df.columns else (
        "id" if "id" in df.columns else None)
    tid = "team_id" if "team_id" in df.columns else None
    print(f"{name:<12} rows={len(df):>9,}  cols={len(df.columns):>3}  "
          f"players={df[aid].nunique() if aid else '?':>8}  "
          f"teams={df[tid].nunique() if tid else '?':>6}")

if "athlete_id" in box.columns and "team_id" in box.columns:
    pt = box.groupby("athlete_id")["team_id"].nunique()
    print(f"\nplayer_box 2026 — players on >1 team_id this season: "
          f"{int((pt > 1).sum()):,} of {len(pt):,} ({100 * (pt > 1).mean():.2f}%)")
    print("  (player_box is GAME-level, so one row per player-game, not per season)")
    dup = box.duplicated(subset=["athlete_id", "game_id"]).sum()
    print(f"  duplicate (athlete_id, game_id) rows: {int(dup):,}")

aid_core = "athlete_id" if "athlete_id" in core.columns else "id"
if aid_core in core.columns:
    d = core.duplicated(subset=[aid_core]).sum()
    print(f"\nplayer_core duplicate {aid_core} rows: {int(d):,}")
    if "team_id" in core.columns:
        pc = core.groupby(aid_core)["team_id"].nunique()
        print(f"player_core players with >1 team_id: {int((pc > 1).sum()):,}")

# ---------------------------------------------------------------- AUDIT 7
rule("AUDIT 7 — athlete_id consistency across files")
core_ids = set(core[aid_core].dropna().astype(str))
box_ids = set(box["athlete_id"].dropna().astype(str))
print(f"player_core unique ids : {len(core_ids):,}")
print(f"player_box  unique ids : {len(box_ids):,}")
inter = box_ids & core_ids
print(f"player_box ids found in player_core: {len(inter):,} "
      f"({100 * len(inter) / len(box_ids):.2f}%)")

shooter_col = next((c for c in shots.columns
                    if "athlete_id" in c.lower() or "shooter" in c.lower()), None)
print(f"\nshots shooter-id column: {shooter_col}")
if shooter_col:
    s_ids = set(shots[shooter_col].dropna().astype(str))
    print(f"shots unique shooter ids: {len(s_ids):,}")
    print(f"  found in player_core: {len(s_ids & core_ids):,} "
          f"({100 * len(s_ids & core_ids) / len(s_ids):.2f}%)")
    print(f"  found in player_box : {len(s_ids & box_ids):,} "
          f"({100 * len(s_ids & box_ids) / len(s_ids):.2f}%)")

# ---------------------------------------------------------------- AUDIT 8
rule("AUDIT 8 — 2026 prospect matching sample (12 verified early entrants)")
# Names/schools from the official nba.com 2026 early-entry table and the
# Wikipedia 2026 early-entrants section (both verified in DATA.md §2, §3.2).
prospects = [
    ("AJ Dybantsa", "BYU"), ("Cameron Boozer", "Duke"),
    ("Mikel Brown Jr.", "Louisville"), ("Darius Acuff Jr.", "Arkansas"),
    ("Nate Ament", "Tennessee"), ("Christian Anderson Jr.", "Texas Tech"),
    ("Brayden Burries", "Arizona"), ("Isaiah Evans", "Duke"),
    ("Keanu Dawes", "Utah"), ("Gabe Dynes", "USC"),
    ("Anton Bonke", "Charlotte"), ("Rowan Brumbaugh", "Tulane"),
]

name_col = next((c for c in ("athlete_display_name", "display_name", "full_name")
                 if c in core.columns), None)
team_name_col = next((c for c in ("team_name", "team_display_name",
                                  "team_location", "team_short_display_name")
                      if c in core.columns), None)
print(f"matching against player_core cols: name={name_col}, team={team_name_col}")

if name_col:
    ref = core[[c for c in (aid_core, name_col, team_name_col) if c]].copy()
    ref["_n"] = ref[name_col].map(norm_name)
    exact = norm = ambig = unmatched = 0
    for pname, school in prospects:
        target = norm_name(pname)
        hits = ref[ref["_n"] == target]
        if len(hits) == 1:
            t = str(hits.iloc[0][team_name_col]) if team_name_col else "?"
            ok = school.lower().split()[0] in t.lower()
            print(f"  {'EXACT ' if ok else 'NAME  '} {pname:<24} -> {t}"
                  f"{'' if ok else f'  (expected {school})'}")
            exact += ok
            norm += (not ok)
        elif len(hits) > 1:
            teams = [str(x) for x in hits[team_name_col]] if team_name_col else []
            match = [t for t in teams if school.lower().split()[0] in t.lower()]
            if len(match) == 1:
                print(f"  EXACT  {pname:<24} -> {match[0]}  "
                      f"(disambiguated from {len(hits)} by school)")
                exact += 1
            else:
                print(f"  AMBIG  {pname:<24} -> {len(hits)} candidates: {teams[:4]}")
                ambig += 1
        else:
            print(f"  UNMATCHED  {pname:<24} (expected {school})")
            unmatched += 1
    tot = len(prospects)
    print(f"\n  exact(name+school) {exact}/{tot} | name-only {norm} | "
          f"ambiguous {ambig} | unmatched {unmatched}")
    print(f"  overall matched: {tot - unmatched - ambig}/{tot} "
          f"({100 * (tot - unmatched - ambig) / tot:.1f}%)")

# ---------------------------------------------------- OPTIONAL — NBA
rule("OPTIONAL — nba/player_season_stats 2026")
nba = pd.read_parquet(NBA / "player_season_stats_2026.parquet")
print(f"rows={len(nba):,}  cols={len(nba.columns)}")
print(f"columns: {list(nba.columns)}")
aid_nba = next((c for c in ("athlete_id", "player_id", "id") if c in nba.columns), None)
if aid_nba:
    print(f"\nunique {aid_nba}: {nba[aid_nba].nunique():,}")
print("\nfill rates:")
print(fill_table(nba).to_string(index=False))
