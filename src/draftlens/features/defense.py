"""Box-score defensive production.

NOT defensive quality. There is no matchup data, no opponent shooting when
defended, no on/off context and no deterrence measure. Steals and blocks are
noisy and position-confounded. Anything built on this module must be labelled
"box-score defensive production" wherever it reaches a user (ML_SPEC 18.3).
"""

import pandas as pd

from draftlens.features.rates import safe_div


def stl_pct(stl, minutes, tm_minutes, opp_possessions):
    stl, minutes, tm_minutes, opp_possessions = (
        pd.to_numeric(pd.Series(x), errors="coerce")
        for x in (stl, minutes, tm_minutes, opp_possessions))
    return 100.0 * safe_div(stl * (tm_minutes / 5.0),
                            minutes * opp_possessions)


def blk_pct(blk, minutes, tm_minutes, opp_fga, opp_fg3a):
    """Blocks as a share of opponent TWO-point attempts faced."""
    blk, minutes, tm_minutes, opp_fga, opp_fg3a = (
        pd.to_numeric(pd.Series(x), errors="coerce")
        for x in (blk, minutes, tm_minutes, opp_fga, opp_fg3a))
    return 100.0 * safe_div(blk * (tm_minutes / 5.0),
                            minutes * (opp_fga - opp_fg3a))
