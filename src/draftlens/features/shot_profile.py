"""Shot-style aggregation from the hoopR play-by-play shot file.

Two verified source hazards constrain everything here (DATA.md 22.3):
  * The shot file contains ONLY MADE free throws, so it is excluded entirely
    and all free-throw metrics come from player_box.
  * Shot coordinates are contaminated with +/-2.1e8 int32 sentinels, so shot
    style is derived from `type_text` and `score_value`, never from coordinates.
"""

import pandas as pd

from draftlens.data.identity.matching import to_int_id
from draftlens.paths import MBB

# hoopR type_text -> stable shot category. Only these four are used; the
# jump-shot subcategories broke schema between 2020 and 2021 (DEC-068).
SHOT_CATEGORIES = {"JumpShot": "jump_shot", "LayUpShot": "layup",
                   "DunkShot": "dunk", "TipShot": "tip"}


def aggregate_shots_frame(sh):
    """Pure shot-aggregation logic (unit-testable)."""
    sh = sh[~sh.type_text.astype(str).str.contains("FreeThrow", na=False)]
    sh["made"] = sh.scoring_play.fillna(False).astype(bool)
    sh["assisted"] = sh.athlete_id_2.notna()
    sh["cat"] = sh.type_text.map(SHOT_CATEGORIES)

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
    for c in SHOT_CATEGORIES.values():
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
