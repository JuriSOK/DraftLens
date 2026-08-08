"""Follow-up checks for the hoopR verification (DATA.md §22).

Corrects the athlete_id comparison to be dtype-safe, resolves school names via
the player_box team mapping, and inventories the NBA long-format stat names.

Run: ./.venv/bin/python scripts/verify_hoopr_sample2.py
"""

import re
import unicodedata
from pathlib import Path

import pandas as pd

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
MBB = RAW / "hoopR-mbb-data"
NBA = RAW / "hoopR-nba-data"


def rule(t):
    print(f"\n{'=' * 78}\n{t}\n{'=' * 78}")


def norm_name(s):
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b\.?", "", s)
    return re.sub(r"\s+", " ", re.sub(r"[^a-z ]", "", s)).strip()


core = pd.read_parquet(MBB / "player_core_2026.parquet")
box = pd.read_parquet(MBB / "player_box_2026.parquet")
shots = pd.read_parquet(MBB / "shots_2026.parquet")

rule("AUDIT 7 (corrected) — dtype-safe athlete_id consistency")
print(f"dtypes: core.athlete_id={core.athlete_id.dtype}  "
      f"box.athlete_id={box.athlete_id.dtype}  "
      f"shots.athlete_id_1={shots.athlete_id_1.dtype}")


def ids(s):
    return set(pd.to_numeric(s, errors="coerce").dropna().astype("int64"))


c_ids, b_ids, s_ids = ids(core.athlete_id), ids(box.athlete_id), ids(shots.athlete_id_1)
print(f"\nplayer_core unique ids: {len(c_ids):,}")
print(f"player_box  unique ids: {len(b_ids):,}")
print(f"shots       unique ids: {len(s_ids):,}")
print(f"\nplayer_box  -> player_core : {len(b_ids & c_ids):,} "
      f"({100 * len(b_ids & c_ids) / len(b_ids):.2f}%)")
print(f"shots       -> player_core : {len(s_ids & c_ids):,} "
      f"({100 * len(s_ids & c_ids) / len(s_ids):.2f}%)")
print(f"shots       -> player_box  : {len(s_ids & b_ids):,} "
      f"({100 * len(s_ids & b_ids) / len(s_ids):.2f}%)")
a_ids = ids(shots.athlete_id_2)
print(f"shots assister ids -> player_box: {len(a_ids & b_ids):,} "
      f"({100 * len(a_ids & b_ids) / len(a_ids):.2f}%)")

rule("AUDIT 3b — shot type taxonomy and assist linkage")
print("type_text distribution:")
vc = shots.type_text.value_counts()
for k, v in vc.items():
    print(f"  {k:<26} {v:>8,}  ({100 * v / len(shots):5.2f}%)")
fg = shots[~shots.type_text.str.contains("FreeThrow", na=False)]
print(f"\nfield-goal attempts (excl. free throws): {len(fg):,}")
print(f"  with assister (athlete_id_2 present): {fg.athlete_id_2.notna().sum():,} "
      f"({100 * fg.athlete_id_2.notna().mean():.2f}%)")
made = fg[fg.scoring_play]
print(f"  made FG: {len(made):,}; of those assisted: "
      f"{100 * made.athlete_id_2.notna().mean():.2f}%")
print(f"\nscore_value distribution: {shots.score_value.value_counts().to_dict()}")
print(f"coordinate_x range: {shots.coordinate_x.min()} .. {shots.coordinate_x.max()}")
print(f"coordinate_y range: {shots.coordinate_y.min()} .. {shots.coordinate_y.max()}")

rule("AUDIT 1b — height/weight/position fill among ROTATION players")
mins = box.groupby("athlete_id")["minutes"].sum()
gp = box[box.did_not_play == False].groupby("athlete_id").size()
rot = set(mins[mins >= 200].index)
print(f"players with >=200 total minutes in 2026: {len(rot):,} of {len(mins):,}")
sub = core[core.athlete_id.isin(rot)]
for c in ["date_of_birth", "age", "height", "weight",
          "position_abbreviation", "experience_years"]:
    nn = sub[c].notna()
    if sub[c].dtype == object:
        nn = nn & (sub[c].astype(str).str.strip() != "")
    print(f"  {c:<24} {100 * nn.mean():6.2f}%  ({int(nn.sum()):,}/{len(sub):,})")

rule("AUDIT 8 (corrected) — prospect matching with school resolution")
teams = (box[["athlete_id", "team_id", "team_display_name"]]
         .drop_duplicates(subset=["athlete_id"], keep="last"))
ref = core[["athlete_id", "display_name", "position_abbreviation"]].merge(
    teams, on="athlete_id", how="left")
ref["_n"] = ref.display_name.map(norm_name)
print(f"player_core rows with a resolved school: "
      f"{ref.team_display_name.notna().sum():,}/{len(ref):,} "
      f"({100 * ref.team_display_name.notna().mean():.1f}%)")

prospects = [
    ("AJ Dybantsa", "BYU"), ("Cameron Boozer", "Duke"),
    ("Mikel Brown Jr.", "Louisville"), ("Darius Acuff Jr.", "Arkansas"),
    ("Nate Ament", "Tennessee"), ("Christian Anderson Jr.", "Texas Tech"),
    ("Brayden Burries", "Arizona"), ("Isaiah Evans", "Duke"),
    ("Keanu Dawes", "Utah"), ("Gabe Dynes", "USC"),
    ("Anton Bonke", "Charlotte"), ("Rowan Brumbaugh", "Tulane"),
]
res = {"exact": 0, "name_only": 0, "ambiguous": 0, "unmatched": 0}
for pname, school in prospects:
    hits = ref[ref._n == norm_name(pname)]
    if len(hits) == 0:
        print(f"  UNMATCHED  {pname:<24} (expected {school})")
        res["unmatched"] += 1
        continue
    key = school.lower().split()[0]
    ok = hits[hits.team_display_name.fillna("").str.lower().str.contains(key)]
    if len(ok) == 1:
        r = ok.iloc[0]
        print(f"  EXACT      {pname:<24} -> {r.team_display_name} "
              f"[{r.position_abbreviation}] id={r.athlete_id}")
        res["exact"] += 1
    elif len(hits) == 1:
        r = hits.iloc[0]
        print(f"  NAME-ONLY  {pname:<24} -> {r.team_display_name} "
              f"(expected {school})")
        res["name_only"] += 1
    else:
        print(f"  AMBIGUOUS  {pname:<24} {len(hits)} candidates: "
              f"{list(hits.team_display_name)[:4]}")
        res["ambiguous"] += 1
print(f"\n  {res}  -> exact name+school: "
      f"{res['exact']}/{len(prospects)} ({100 * res['exact'] / len(prospects):.1f}%)")

rule("OPTIONAL (corrected) — NBA player_season_stats 2026 stat inventory")
nba = pd.read_parquet(NBA / "player_season_stats_2026.parquet")
print(f"LONG format: {len(nba):,} rows, {nba.athlete_id.nunique():,} players, "
      f"{nba.stat_name.nunique()} distinct stat_name values")
print(f"categories: {sorted(nba.category.unique())}")
print("\nstat_name inventory by category:")
for cat in sorted(nba.category.unique()):
    names = sorted(nba[nba.category == cat].stat_name.unique())
    print(f"\n  [{cat}] ({len(names)})")
    for i in range(0, len(names), 6):
        print("    " + ", ".join(names[i:i + 6]))
