"""Rate primitives shared by every basketball feature domain.

SAFE DIVISION POLICY (DEC-069): an undefined ratio is NULL, never 0 and never
infinity. 0 made from 0 attempts is UNKNOWN, not 0%. No epsilon is ever added.
This is a leakage guard as much as a correctness one — substituting 0 would
encode "never attempted" as "attempted and failed", and attempt frequency
correlates with the draft outcome (DEC-073).

Nothing in this package reads draft outcome, pick, NBA data, age or DOB.
"""

import numpy as np
import pandas as pd

# Free-throw possession coefficient used by the conventional TS%, possession,
# usage and turnover-rate formulas. Named rather than hidden as a literal.
FT_POSSESSION_COEF = 0.44


def safe_div(num, den):
    """Element-wise division that yields NaN wherever the result is undefined.

    Undefined means: denominator missing, denominator <= 0, or numerator
    missing. Never returns inf; never substitutes 0 for an undefined ratio.
    """
    num = pd.to_numeric(pd.Series(num), errors="coerce")
    den = pd.to_numeric(pd.Series(den), errors="coerce")
    den = den.reindex(num.index) if len(den) == len(num) else den
    ok = den.notna() & (den > 0) & num.notna()
    out = pd.Series(np.nan, index=num.index, dtype="float64")
    out[ok] = num[ok].astype("float64") / den[ok].astype("float64")
    return out.replace([np.inf, -np.inf], np.nan)


def per_game(stat, games):
    return safe_div(stat, games)


def per_40(stat, minutes):
    """40 * stat / minutes. NULL when minutes are 0 or missing."""
    stat = pd.to_numeric(pd.Series(stat), errors="coerce")
    return safe_div(40.0 * stat, minutes)


def per_100(stat, possessions):
    stat = pd.to_numeric(pd.Series(stat), errors="coerce")
    return safe_div(100.0 * stat, possessions)


def team_possessions(fga, fta, orb, tov):
    """Conventional estimate: FGA + 0.44*FTA - ORB + TOV.

    Returned as a plain numeric series (may legitimately be 0 only for an empty
    team-season, which safe_div then treats as undefined downstream).
    """
    fga, fta, orb, tov = (pd.to_numeric(pd.Series(x), errors="coerce")
                          for x in (fga, fta, orb, tov))
    return fga + FT_POSSESSION_COEF * fta - orb + tov
