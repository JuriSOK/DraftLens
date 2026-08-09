"""Physical attributes from the hoopR player core file.

Height and weight coverage vary by season (76.7-99.2% and 57.1-94.7%), so both
are treated as source-missing rather than structurally absent. Date of birth is
NOT read here: its availability is outcome-correlated and it is prohibited as a
model feature (ML_SPEC 8.2).
"""

import pandas as pd

from draftlens.data.identity.matching import to_int_id
from draftlens.paths import MBB


def physical(year, ids):
    core = pd.read_parquet(MBB / "player_core" / f"player_core_{year}.parquet")
    core["athlete_id"] = to_int_id(core.athlete_id)
    core = core[core.athlete_id.isin(ids)]
    keep = core[["athlete_id", "position_abbreviation", "height", "weight",
                 "experience_years"]].copy()
    return keep.rename(columns={"position_abbreviation": "hoopr_position"})
