"""The NBA reference pool: exactly one representation per unique player.

Three things this module is responsible for, each with a way it could go wrong:

  UNIQUENESS. A player has several seasons in the window. The comparable pool
  must hold ONE row per player, or the top three could come back as
  "Player A 2023, Player A 2024, Player B 2024" — three rows, two people.

  ELIGIBILITY. Low-minute seasons produce unstable rates: a 40-minute season
  can show a 100% three-point rate. A minimum playing-time rule keeps the pool
  to players with a genuine NBA role, without pruning it so hard that role
  players disappear.

  IDENTITY. Players are collapsed on `athlete_id`, never on name. Audited over
  2021-2025: 0 ids carry more than one name and 0 names map to more than one
  id, so the ids are stable and are the correct key.

The reference window is FROZEN and excludes 2026 entirely — both because 2026
is this project's sealed holdout label and because a recent, coherent pool is
what makes a comparison recognisable.
"""

import json

import numpy as np
import pandas as pd

from comparables.nba_features import load_player_seasons
from paths import CONFIG, interim

CONFIG_PATH = CONFIG / "comparables.json"
OUT = interim("comparables")
REFERENCE_FILE = OUT / "nba_reference_pool.parquet"

# Frozen NBA reference window: five completed seasons, ending before the
# holdout year. Chosen for modern role relevance and pool size, never because
# particular players appear in it.
REFERENCE_SEASONS = list(range(2021, 2026))
HOLDOUT_YEAR = 2026

# A genuine NBA rotation role. ~25 minutes over 30 games, or ~9 over a full
# season. Set from the minutes distribution, never from how any NCAA prospect's
# comparables look.
MIN_MINUTES = 750
MIN_GAMES = 30

# Up to this many recent qualifying seasons in the multi-season representation.
RECENT_SEASONS = 3

# ESPN mixes coarse and fine position labels. This mapping is deterministic and
# purely lexical — no position is ever inferred from statistics.
POSITION_3 = {"PG": "G", "SG": "G", "G": "G",
              "SF": "F", "PF": "F", "F": "F",
              "C": "C"}


def load_config(path=CONFIG_PATH):
    return json.loads(path.read_text())


def eligible_seasons(ps=None, min_minutes=MIN_MINUTES, min_games=MIN_GAMES,
                     seasons=None):
    """Player-seasons that represent a genuine NBA role."""
    seasons = seasons if seasons is not None else REFERENCE_SEASONS
    assert HOLDOUT_YEAR not in set(seasons), "HOLDOUT GUARD: 2026 in the pool"
    ps = ps if ps is not None else load_player_seasons(seasons)
    ps = ps[ps.season.isin(seasons)]
    ok = (pd.to_numeric(ps.minutes, errors="coerce") >= min_minutes) & \
         (pd.to_numeric(ps.games_played, errors="coerce") >= min_games)
    out = ps[ok].copy()
    out["position_3"] = out.athlete_position_abbreviation.map(POSITION_3) \
        .fillna("UNKNOWN")
    return out.reset_index(drop=True)


def latest_season_pool(eligible, metrics):
    """Representation A: each player's most recent qualifying season.

    Easy to explain and reflects a current role; carries one season of noise.
    """
    idx = eligible.sort_values("season").groupby("athlete_id").tail(1).index
    pool = eligible.loc[idx].copy()
    pool["reference_seasons"] = pool.season.map(lambda s: [int(s)])
    pool["n_reference_seasons"] = 1
    return _finalise(pool, metrics)


def recent_multi_season_pool(eligible, metrics, n_seasons=RECENT_SEASONS):
    """Representation B: minutes-weighted mean over the last `n_seasons`.

    Minutes weighting is the honest aggregator here: a 2,400-minute season
    describes a player's role better than a 780-minute one, and every metric in
    the space is already a rate or a ratio, so weighting by the exposure that
    produced it is the same operation the rates themselves perform.
    """
    e = eligible.sort_values(["athlete_id", "season"])
    e = e.groupby("athlete_id").tail(n_seasons).copy()
    w = pd.to_numeric(e.minutes, errors="coerce").to_numpy(dtype="float64")

    rows = {}
    for m in metrics:
        v = pd.to_numeric(e[m], errors="coerce").to_numpy(dtype="float64")
        ok = np.isfinite(v) & np.isfinite(w)
        tmp = pd.DataFrame({"athlete_id": e.athlete_id.to_numpy(),
                            "wv": np.where(ok, v * w, np.nan),
                            "w": np.where(ok, w, np.nan)})
        agg = tmp.groupby("athlete_id").sum(min_count=1)
        rows[m] = agg.wv / agg.w

    pool = pd.DataFrame(rows)
    meta = e.groupby("athlete_id").agg(
        athlete_display_name=("athlete_display_name", "last"),
        athlete_position_abbreviation=("athlete_position_abbreviation", "last"),
        position_3=("position_3", "last"),
        team_display_name=("team_display_name", "last"),
        minutes=("minutes", "sum"),
        games_played=("games_played", "sum"),
        season=("season", "max"),
        n_reference_seasons=("season", "size"))
    ref = e.groupby("athlete_id").season.apply(
        lambda s: sorted(int(x) for x in s)).rename("reference_seasons")
    pool = meta.join(pool).join(ref).reset_index()
    return _finalise(pool, metrics)


def career_pool(eligible, metrics):
    """Representation C: minutes-weighted mean over EVERY qualifying season.

    DIAGNOSTIC ONLY. Averaging a whole career mixes career stages and roles and
    can manufacture a player who never existed in any single season.
    """
    return recent_multi_season_pool(eligible, metrics,
                                    n_seasons=len(REFERENCE_SEASONS))


def _finalise(pool, metrics):
    pool = pool.reset_index(drop=True)
    assert pool.athlete_id.is_unique, "the NBA pool holds a duplicate player"
    keep = ["athlete_id", "athlete_display_name",
            "athlete_position_abbreviation", "position_3", "team_display_name",
            "season", "reference_seasons", "n_reference_seasons", "minutes",
            "games_played"] + list(metrics)
    return pool[[c for c in keep if c in pool.columns]]


def build_pool(representation="RECENT_MULTI_SEASON", metrics=None,
               seasons=None, min_minutes=MIN_MINUTES, min_games=MIN_GAMES):
    """The frozen NBA reference pool, one row per unique player."""
    from comparables.space import COMMON_METRICS
    metrics = metrics if metrics is not None else COMMON_METRICS
    eligible = eligible_seasons(min_minutes=min_minutes, min_games=min_games,
                                seasons=seasons)
    if representation == "LATEST_SEASON":
        return latest_season_pool(eligible, metrics)
    if representation == "RECENT_MULTI_SEASON":
        return recent_multi_season_pool(eligible, metrics)
    if representation == "CAREER":
        return career_pool(eligible, metrics)
    raise ValueError(representation)


def load_pool(path=REFERENCE_FILE):
    if not path.exists():
        raise FileNotFoundError(
            f"{path} missing — run scripts/build_nba_reference.py")
    return pd.read_parquet(path)


# --------------------------------------------------------- NCAA peer side
NCAA_REFERENCE_FILE = OUT / "ncaa_comparable_reference.parquet"

# Same rotation-player filter the Team Need reference uses, for the same
# reason: a percentile against a population of eight-minute walk-ons is not a
# meaningful basketball statement.
NCAA_MIN_MINUTES = 200
NCAA_MIN_GAMES = 10


def build_ncaa_reference(years, metrics=None, min_minutes=NCAA_MIN_MINUTES,
                         min_games=NCAA_MIN_GAMES, log=print):
    """The NCAA peer population a prospect is ranked against.

    Built by the same `_season_frame` the Team Need reference uses, so a
    prospect's value and its peer group are produced by identical code.
    """
    from comparables.space import COMMON_METRICS
    from team_need.reference import _season_frame
    metrics = metrics if metrics is not None else COMMON_METRICS
    assert HOLDOUT_YEAR not in set(years), "HOLDOUT GUARD: 2026 in the reference"

    frames = []
    for y in years:
        d = _season_frame(y)
        n_all = len(d)
        d = d[(d.minutes >= min_minutes) & (d.games_played >= min_games)]
        log(f"  {y}: {n_all:>6} NCAA players -> {len(d):>5} in reference")
        keep = ["athlete_id", "position_3"] + [m for m in metrics
                                               if m in d.columns]
        sub = d[keep].copy()
        sub["season"] = y
        frames.append(sub)
    return pd.concat(frames, ignore_index=True)


def load_ncaa_reference(path=NCAA_REFERENCE_FILE):
    if not path.exists():
        raise FileNotFoundError(
            f"{path} missing — run scripts/build.py comparables")
    return pd.read_parquet(path)
