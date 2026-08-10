"""The 2026 ALL-DECLARED product board — an additional, exploratory ranking
generated AFTER the frozen 2026 holdout replay (`replay.py`), using the
already-frozen methodology on a LARGER population.

This is NOT the frozen 2026 holdout. `replay.py`'s 26-prospect
FINAL_ENTRY population and its one-time evaluation are untouched by this
module and stay the sole authority on holdout performance. This module exists
because the product wants to show every NCAA player who initially declared
for the draft, including the 34 who later withdrew — a product/coverage
decision, not a re-run of the science.

Two firewalls apply here exactly as in replay.py:
  * DECLARATION/WITHDRAWAL STATUS NEVER ENTERS SCORING. `population_status`
    (FINAL_ENTRY/WITHDRAWN) is joined onto the output ONLY after every model
    prediction and board computation is complete — never as a feature, never
    as a filter that could change model fitting.
  * NO DRAFT OUTCOME. This module never calls `data.population.load_targets`
    or reads `data/raw/draft_targets/`. (Unlike replay.py's Part A, it does
    not need a target-access guard: 2026 outcomes were already unsealed by
    replay.evaluate() before this module is ever used, so there is nothing
    left to seal — the guard here is scientific, not chronological. It exists
    because this ranking's answer must not depend on who was actually
    drafted, not because the draft hasn't happened.)

Every model call below is byte-identical machinery to replay.py's — same
frozen Draft Probability / Draft Order fits, same General Board formula, same
Team Need and NBA Comparables computation — applied to a different population
frame. Draft Probability and Draft Order are row-independent predictions, so a
FINAL_ENTRY prospect's own probability/quality signal is numerically identical
whether scored here or in the frozen 26-only replay. Overall Score is NOT
row-independent — it is a class-relative percentile of the combined signal, so
a FINAL_ENTRY prospect's rank/Overall Score under All Declared legitimately
differs from their frozen Final Entrants board position. The frozen 26-only
artifact (`replay.PREDICTIONS_PATH`) remains the sole source for Final
Entrants numbers; this module's output is never substituted for it.
"""

import json
from datetime import datetime, timezone

import pandas as pd

from paths import DATA, ROOT

YEAR = 2026

OUT_DIR = DATA / "processed" / "2026"
DECLARED_PREDICTIONS_PATH = OUT_DIR / "draftlens_2026_declared_predictions.parquet"
DECLARED_FEATURES_PATH = OUT_DIR / "draftlens_2026_declared_features.parquet"
DECLARED_COMPARABLES_PATH = OUT_DIR / "draftlens_2026_declared_comparables.json"
DECLARED_PROVENANCE_PATH = OUT_DIR / "declared_provenance.json"
DECLARED_AUDIT_PATH = OUT_DIR / "declared_audit.json"
DECLARED_INSUFFICIENT_PATH = OUT_DIR / "declared_insufficient_data.json"


def _sha256_file(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------- target-free build
def build_declared_frame(year=YEAR):
    """The declared population's engineered features — matched, target-free.

    Mirrors `data.build.build_year` + `features.basketball.assemble`'s
    population -> raw primitives -> engineered layer, but for the DECLARED
    pool instead of `data.population.load_population`, and reusing
    `data.build.raw_prospect_features` rather than duplicating its matching
    and aggregation logic. Never calls `data.population.load_targets`.

    Returns (matched, feats, audit) where `matched` is the full declared
    population with match diagnostics, `feats` holds only the SCOREABLE rows
    (matched to hoopR with recorded box-score minutes), and `audit` is a dict
    of official/matched/scoreable/unmatched/insufficient-data counts.
    """
    from data.build import raw_prospect_features
    from data.matching import load_overrides, season_index
    from data.population import load_declared
    from features.basketball import engineer_year
    from replay import assert_target_free

    declared = load_declared(year)
    if declared is None:
        raise FileNotFoundError(
            f"no declared-pool snapshot for {year} — run "
            f"scripts/acquire.py declared --years {year} first")
    assert_target_free(declared, "declared population")

    idx = season_index(year)
    overrides = load_overrides()
    matched, raw, dupes, box_rows = raw_prospect_features(
        year, declared, idx, overrides)
    assert_target_free(raw, "declared raw features")

    full = engineer_year(year, raw)
    scoreable_mask = (matched.hoopr_athlete_id.notna()
                      & raw.games_played.notna()).reset_index(drop=True)
    feats = full[scoreable_mask].reset_index(drop=True)
    assert_target_free(feats, "declared engineered features")

    n_official = len(declared)
    n_matched = int(matched.hoopr_athlete_id.notna().sum())
    n_scoreable = int(scoreable_mask.sum())
    audit = dict(
        official_declared=n_official,
        matched=n_matched,
        unmatched=n_official - n_matched,
        scoreable=n_scoreable,
        insufficient_data=n_official - n_scoreable,
        box_dupe_rows_removed=int(dupes),
    )
    return matched, feats, audit


# ------------------------------------------------------------------------ score
def score_declared(year=YEAR):
    """Score the declared pool with the frozen methodology (Part A only —
    outcomes are never touched here). Returns a dict of everything an
    operator needs to inspect the run."""
    import replay
    from data.population import population_status
    from replay import (assert_target_free, build_2026_board,
                        build_2026_comparables, build_2026_team_need,
                        fit_draft_order_2026, fit_draft_probability_2026)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    matched, feats, audit = build_declared_frame(year)
    print(f"Declared population: official={audit['official_declared']} "
         f"matched={audit['matched']} scoreable={audit['scoreable']} "
         f"unmatched={audit['unmatched']} insufficient_data="
         f"{audit['insufficient_data']}")

    feats = feats.sort_values("canonical_prospect_id").reset_index(drop=True)
    feats.to_parquet(DECLARED_FEATURES_PATH, index=False)

    # Declared-but-unscoreable prospects: identity/status only, never a
    # fabricated score. Shown in the product as "Insufficient data".
    status_all = population_status(year)
    scoreable_ids = set(feats.canonical_prospect_id)
    insufficient = status_all[~status_all.canonical_prospect_id.isin(scoreable_ids)]
    DECLARED_INSUFFICIENT_PATH.write_text(json.dumps(
        insufficient[["canonical_prospect_id", "player_name", "college",
                      "position", "population_status"]]
        .to_dict(orient="records"), indent=2, sort_keys=True, default=str))
    draft_probability = fit_draft_probability_2026(feats)
    draft_order_signal = fit_draft_order_2026(feats)
    board, draft_size = build_2026_board(feats, draft_probability,
                                         draft_order_signal)

    team_need_df, _ = build_2026_team_need(feats)
    comparables = build_2026_comparables(feats)

    predictions = board.merge(
        team_need_df.drop(columns=["player_name", "college", "position_3"]),
        on="canonical_prospect_id", how="left")
    predictions["_draft_order_raw_pick_signal_INTERNAL_ONLY"] = draft_order_signal

    # Population status is joined ONLY now, after every model/board
    # computation is finished — display metadata, never a scoring input.
    predictions = predictions.merge(
        status_all[["canonical_prospect_id", "population_status"]],
        on="canonical_prospect_id", how="left")
    assert predictions.population_status.notna().all(), \
        "a scored prospect has no population_status — investigate matching"

    predictions = predictions.sort_values(
        "canonical_prospect_id").reset_index(drop=True)
    assert_target_free(predictions, "declared prediction artifact")

    predictions.to_parquet(DECLARED_PREDICTIONS_PATH, index=False)
    comparables_out = {str(k): v for k, v in comparables.items()}
    DECLARED_COMPARABLES_PATH.write_text(
        json.dumps(comparables_out, indent=2, sort_keys=True, default=str))
    DECLARED_AUDIT_PATH.write_text(json.dumps(audit, indent=2, sort_keys=True))

    provenance = dict(
        generated_at_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        analytics_freeze_tag="analytics-freeze-pre-2026",
        year=year,
        draft_size=draft_size,
        audit=audit,
        official_source=replay_declared_source(year),
        prediction_artifact=dict(
            path=str(DECLARED_PREDICTIONS_PATH.relative_to(ROOT)),
            sha256=_sha256_file(DECLARED_PREDICTIONS_PATH),
            rows=int(len(predictions))),
        note="Additional product exploration generated AFTER the frozen 2026 "
            "holdout replay, using the same frozen methodology on a larger "
            "population (all NCAA players who initially declared, including "
            "34 who later withdrew). This is NOT the frozen holdout "
            "evaluation population or a re-scoring of it.",
    )
    DECLARED_PROVENANCE_PATH.write_text(
        json.dumps(provenance, indent=2, sort_keys=True))

    print(f"\n2026 ALL-DECLARED BOARD — {len(predictions)} scoreable prospects")
    print(f"  artifact  {DECLARED_PREDICTIONS_PATH.relative_to(ROOT)}")
    print(f"  provenance  {DECLARED_PROVENANCE_PATH.relative_to(ROOT)}")

    return dict(predictions=predictions, audit=audit, provenance=provenance)


def replay_declared_source(year=YEAR):
    from data.wikipedia import DECLARED_SNAPSHOTS
    return DECLARED_SNAPSHOTS.get(year)
