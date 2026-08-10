"""The 2027 PROJECTED WATCHLIST — explicitly NOT an official NBA early-entry
declaration list, because none exists yet.

There is no official NBA 2027 early-entry announcement in the repository (see
`data.wikipedia.DECLARED_SNAPSHOTS`, which has no 2027 entry). This module
instead builds a reproducible, multi-source PROJECTED population from public
NBA Draft coverage, acquired into
`data/raw/draft_watchlist/draft_watchlist_sources_2027.csv`
(source, publication_date, url, rank, player_name, school, class_year,
is_ncaa — one row per (source, player) appearance, three sources: CBS
Sports, Sports Illustrated, Yahoo Sports).

CONSENSUS RULE (`MIN_SOURCES = 2`): an NCAA-affiliated player must be named
on at least 2 of the 3 approved boards to enter the watchlist. This is a
deliberately conservative membership rule — a single outlet's outlier pick
does not seat a player, and no name is manually added or removed.
International-only players (no US college listed) are excluded entirely:
DraftLens has no comparable NCAA feature space for them (`is_ncaa=False`
rows are dropped before the consensus count).

WHAT THE SOURCE RANKINGS ARE USED FOR: membership only. `rank` is read to
determine WHO is on the list; it is never stored as a DraftLens feature,
never used to order the watchlist, and never influences Team Need or
Comparables scoring. The watchlist itself is unordered.

WHAT THIS MODULE NEVER DOES: fit or apply Draft Probability, Draft Order, or
the General Board formula to this population. Those models were validated on
the declared-early-entrant sampling frame (`data.population.load_population`)
— a 2027 media projection is a different sampling frame with different
selection dynamics, so applying that model here would misrepresent what its
output means. Team Need and NBA Comparables ARE computed for returning
players (see `build_watchlist_frame`/`score_returning` below) because both
are peer-percentile computations against the full NCAA season population,
not fitted against any draft-outcome-labelled population — the same
reasoning that already lets them run on any NCAA player-season.

RETURNING vs INCOMING. A watchlist player is "returning" if hoopR's most
recent completed season (2026, i.e. the 2025-26 academic year) has a
matched, played record for them — sophomores, juniors, seniors. A player who
has never played an NCAA game yet (incoming freshmen entering fall 2026) is
simply absent from that season's data and is classified "incoming" by that
absence, never by trusting the source article's stated class year. No
statistic is fabricated for incoming players.
"""

import json

import pandas as pd

from paths import DATA, RAW, ROOT

WATCHLIST_DIR = RAW / "draft_watchlist"
SOURCES_PATH = WATCHLIST_DIR / "draft_watchlist_sources_2027.csv"

YEAR = 2027
STATS_SEASON = 2026  # most recent completed NCAA season available
MIN_SOURCES = 2

OUT_DIR = DATA / "processed" / "2027"
RETURNING_PREDICTIONS_PATH = OUT_DIR / "watchlist_2027_returning.parquet"
RETURNING_COMPARABLES_PATH = OUT_DIR / "watchlist_2027_comparables.json"
INCOMING_PATH = OUT_DIR / "watchlist_2027_incoming.json"
PROVENANCE_PATH = OUT_DIR / "watchlist_2027_provenance.json"


def load_sources():
    """Raw (source, player) appearance rows, or None if not yet acquired."""
    if not SOURCES_PATH.exists():
        return None
    return pd.read_csv(SOURCES_PATH)


def sources_summary():
    df = load_sources()
    if df is None:
        return []
    out = []
    for source, g in df.groupby("source"):
        out.append(dict(
            name=source,
            url=g.url.iloc[0],
            publicationDate=g.publication_date.iloc[0],
            playersListed=len(g),
        ))
    return sorted(out, key=lambda r: r["name"])


def build_consensus():
    """The reproducible watchlist population: NCAA-affiliated players named
    on >= MIN_SOURCES of the approved boards. Returns None if no source file
    has been acquired yet — never a fabricated population."""
    from data.matching import normalize_name

    df = load_sources()
    if df is None:
        return None

    ncaa = df[df.is_ncaa.astype(str) == "True"].copy()
    ncaa["normalized_name"] = ncaa.player_name.map(normalize_name)

    n_sources = ncaa.groupby("normalized_name").source.nunique()
    consensus_names = set(n_sources[n_sources >= MIN_SOURCES].index)

    first = (ncaa.sort_values("source")
             .groupby("normalized_name", as_index=False).first())
    pop = first[first.normalized_name.isin(consensus_names)].copy()

    src_lists = (ncaa.groupby("normalized_name").source
                .apply(lambda s: sorted(set(s))))
    pop["sources"] = pop.normalized_name.map(src_lists)
    pop["n_sources"] = pop["sources"].map(len)

    pop["draft_year"] = YEAR
    pop = pop.rename(columns={"player_name": "player_name",
                              "school": "college"})
    pop["canonical_prospect_id"] = (
        f"{YEAR}-" + pop.normalized_name.str.replace(" ", "_"))
    pop["wikipedia_title"] = ""
    return pop[["canonical_prospect_id", "draft_year", "player_name",
               "normalized_name", "college", "class_year", "sources",
               "n_sources", "wikipedia_title"]].reset_index(drop=True)


# --------------------------------------------------------------- matching
def build_watchlist_frame():
    """Match the consensus population against hoopR's most recent season.

    Returns (matched, feats_returning, incoming_records) where `matched`
    carries match diagnostics for everyone, `feats_returning` is the
    engineered feature frame for players with a played record (never calls
    `data.population.load_targets`), and `incoming_records` is identity-only
    for players with no NCAA record yet.
    """
    from data.build import raw_prospect_features
    from data.matching import load_overrides, season_index
    from features.basketball import engineer_year
    from replay import assert_target_free

    pop = build_consensus()
    if pop is None:
        return None, None, None
    assert_target_free(pop, "2027 watchlist population")

    idx = season_index(STATS_SEASON)
    overrides = load_overrides()
    matched, raw, dupes, box_rows = raw_prospect_features(
        STATS_SEASON, pop, idx, overrides)
    assert_target_free(raw, "2027 watchlist raw features")

    scoreable_mask = (matched.hoopr_athlete_id.notna()
                      & raw.games_played.notna()).reset_index(drop=True)
    full = engineer_year(STATS_SEASON, raw)
    feats_returning = full[scoreable_mask].reset_index(drop=True)
    assert_target_free(feats_returning, "2027 watchlist returning features")

    incoming = matched[~scoreable_mask.to_numpy()][
        ["canonical_prospect_id", "player_name", "normalized_name",
         "college", "class_year", "sources"]].copy()
    incoming["class_year"] = incoming.class_year.where(
        incoming.class_year.notna(), None)
    incoming_records = incoming.to_dict(orient="records")

    return matched, feats_returning, incoming_records


# ---------------------------------------------------------------- scoring
def score_returning(feats_returning):
    """Team Need + NBA Comparables ONLY — reusing replay.py's helpers
    unchanged, since both are peer-percentile computations against the full
    NCAA season population, not fitted against a draft-outcome-labelled
    sample. Deliberately does NOT call fit_draft_probability_2026,
    fit_draft_order_2026, or build_2026_board — see module docstring."""
    from replay import build_2026_comparables, build_2026_team_need

    team_need_df, _ = build_2026_team_need(feats_returning)
    comparables = build_2026_comparables(feats_returning)
    return team_need_df, comparables


def build_watchlist(write=True):
    matched, feats_returning, incoming_records = build_watchlist_frame()
    if matched is None:
        return None

    provenance = dict(
        year=YEAR,
        label="2027 Projected Watchlist",
        consensus_rule=f"NCAA-affiliated player named on >= {MIN_SOURCES} "
                       f"of 3 approved public boards",
        min_sources=MIN_SOURCES,
        sources=sources_summary(),
        watchlist_size=int(len(matched)),
        returning=int(len(feats_returning)),
        incoming=int(len(incoming_records)),
    )

    team_need_df = comparables = None
    if len(feats_returning):
        team_need_df, comparables = score_returning(feats_returning)
        id_cols = ["canonical_prospect_id", "class_year"]
        predictions = feats_returning.merge(
            matched[id_cols], on="canonical_prospect_id", how="left")
        predictions = predictions.merge(
            team_need_df.drop(columns=["player_name", "college", "position_3"]),
            on="canonical_prospect_id", how="inner")

    if write:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        if team_need_df is not None:
            predictions.to_parquet(RETURNING_PREDICTIONS_PATH, index=False)
            comp_out = {str(k): v for k, v in comparables.items()}
            RETURNING_COMPARABLES_PATH.write_text(
                json.dumps(comp_out, indent=2, sort_keys=True, default=str))
        INCOMING_PATH.write_text(
            json.dumps(incoming_records, indent=2, sort_keys=True, default=str))
        PROVENANCE_PATH.write_text(json.dumps(provenance, indent=2, sort_keys=True))

    return dict(matched=matched, feats_returning=feats_returning,
               incoming_records=incoming_records, provenance=provenance)
