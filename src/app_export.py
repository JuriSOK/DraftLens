"""The public application data export — the ONE thing the frontend reads.

Turns the already-frozen, already-hashed 2026 prediction artifacts
(`src/replay.py`) and the additional, separately-frozen all-declared product
board (`src/declared.py`) into a small, deterministic, target-free JSON file
the static React app consumes directly. This module performs NO analytical
computation of its own: every number here was already produced by the frozen
Draft Probability / Draft Order / General Board / Team Need / NBA Comparables
systems. It only selects, renames and rounds fields for display.

TWO 2026 populations, kept explicitly distinct:
  * finalEntrantsBoard — the 26-prospect FROZEN holdout board (`replay.py`),
    read from its artifact untouched. This is the population the one-time
    2026 evaluation actually scored.
  * declaredBoard — the larger ALL-DECLARED product board (`declared.py`,
    ~60 prospects including 34 who later withdrew), an additional
    exploration generated AFTER the holdout with the same frozen methodology.
    Never presented as the holdout population or its evaluation result.

Nothing here may read `_draft_order_raw_pick_signal_INTERNAL_ONLY` or any
2026 outcome field — `assert_no_leakage` checks the finished payload before
it is written, the same discipline `replay.assert_target_free` applies to the
prediction artifacts themselves. Declaration/withdrawal status
(`populationStatus`) is display metadata only; it is attached after every
model prediction, never before.
"""

import hashlib
import json
from datetime import datetime, timezone

import pandas as pd

from paths import ROOT

APP_DATA_PATH = ROOT / "app" / "public" / "data" / "draftlens_2026.json"

# Every field name (after camelCase conversion) that would leak a 2026
# outcome into the product. Checked recursively over the finished payload.
PROHIBITED_FIELDS = {
    "drafted", "pick", "round", "draftingTeam", "actualPick", "draftTeam",
    "actualRound", "actualDraftPosition", "actualDrafted",
    "_draft_order_raw_pick_signal_internal_only",
}

PROFILE_KEYS = {
    "SHOOTER": "shooter", "SLASHER": "slasher", "PLAYMAKER": "playmaker",
    "THREE_AND_D": "threeAndD", "RIM_PROTECTOR": "rimProtector",
    "STRETCH_BIG": "stretchBig",
}

# Custom Team Need mode's approved sliders (config/team_need.json
# custom_mode.supported_dimensions). RIM_PRESSURE is explicitly NOT approved
# for the custom UI; ATHLETICISM does not exist as a product concept at all
# (there is no data source for it — see docs/METHODOLOGY.md). Do not add to
# this list without a product decision recorded in config/team_need.json.
CUSTOM_DIMENSIONS = ["shooting", "playmaking", "defensiveProduction",
                     "rebounding", "size"]

YEAR = 2026


def _r1(x):
    """Round to 1 decimal, or None. Never fabricates a value for NaN."""
    if x is None or pd.isna(x):
        return None
    return round(float(x), 1)


def _clean_str(x):
    """A string field, or None — never the literal NaN token, which is not
    valid JSON and breaks JSON.parse in the browser."""
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    return str(x)


def _r3(x):
    if x is None or pd.isna(x):
        return None
    return round(float(x), 3)


def _rint(x):
    if x is None or pd.isna(x):
        return None
    return int(round(float(x)))


def _profile(row, prefix):
    fit = row.get(f"team_need_{prefix}_fit_score")
    elig = row.get(f"team_need_{prefix}_eligibility")
    return {"fitScore": _rint(fit), "eligibility": elig}


def _profiles(row):
    return {v: _profile(row, k.lower()) for k, v in PROFILE_KEYS.items()}


def _board(row):
    return {
        "rank": int(row.board_rank),
        "overallScore": int(row.overall_score),
        "draftProbability": _r3(row.stage_a_probability),
        "draftOrderSignal": _r3(row.stage_b_quality),
    }


def _stats(feats_row):
    return {
        "heightInches": _r1(feats_row.get("height")),
        "pointsPer40": _r1(feats_row.points_per_40),
        "reboundsPer40": _r1(feats_row.reb_per_40),
        "assistsPer40": _r1(feats_row.assists_per_40),
        "stealsPer40": _r1(feats_row.get("steals_per_40")),
        "blocksPer40": _r1(feats_row.get("blocks_per_40")),
        "turnoversPer40": _r1(feats_row.get("turnovers_per_40")),
        "threePointPct": _r3(feats_row.three_point_pct),
        "threePointAttempts": _rint(feats_row.get("three_points_attempted")),
        "ftPct": _r3(feats_row.ft_pct),
        "ftAttempts": _rint(feats_row.get("free_throws_attempted")),
        "tsPct": _r3(feats_row.ts_pct),
        "fgAttempts": _rint(feats_row.get("field_goals_attempted")),
        "minutesPerGame": _r1(feats_row.minutes_per_game),
        "gamesPlayed": _rint(feats_row.games_played),
    }


def _dimensions(row):
    return {
        "shooting": _r1(row.dimension_shooting),
        "playmaking": _r1(row.dimension_playmaking),
        "defensiveProduction": _r1(row.dimension_box_score_defensive_production),
        "rebounding": _r1(row.dimension_rebounding),
        "size": _r1(row.dimension_size),
        "rimPressure": _r1(row.dimension_rim_pressure),
    }


def _comparable(entry):
    close = [
        dict(label=d["label"], prospectPercentile=_r1(d["prospect_percentile"]),
            nbaPercentile=_r1(d["nba_percentile"]))
        for d in entry.get("closest_dimensions", [])[:3]
    ]
    diffs = [
        dict(label=d["label"], prospectPercentile=_r1(d["prospect_percentile"]),
            nbaPercentile=_r1(d["nba_percentile"]))
        for d in entry.get("largest_differences", [])[:1]
    ]
    return dict(
        rank=entry["rank"],
        nbaPlayerName=entry["nba_player_name"],
        nbaHeightInches=_rint(entry.get("nba_height_inches")),
        similarityScore=_rint(entry["similarity_score"]),
        referenceSeasons=list(entry["reference_seasons"]),
        closestDimensions=close,
        differences=diffs,
    )


def _comparables(pid, comparables_json):
    entry = comparables_json.get(pid)
    if entry is None or entry.get("status") != "OK":
        return []
    return [_comparable(c) for c in entry["comparables"]]


def _load_photo_index():
    """prospect_id -> verified photo metadata. Only rows the acquisition
    marked OK are exported, so a prospect whose identity was ambiguous or
    whose licence was rejected simply has no photo — never a broken or
    unattributed one."""
    from data.photos import load_photos

    df = load_photos()
    if df is None:
        return {}
    out = {}
    for r in df.itertuples():
        if str(r.status) != "OK":
            continue
        thumb = str(r.thumbnail_url or "").strip()
        license_name = str(r.license or "").strip()
        attribution = str(r.attribution or "").strip()
        # Attribution and licence are REQUIRED for a photo to ship.
        if not thumb or not license_name or not attribution:
            continue
        out[str(r.prospect_id)] = dict(
            thumbnailUrl=thumb,
            sourceUrl=str(r.source_url or "").strip() or None,
            attribution=attribution,
            license=license_name,
            licenseUrl=str(r.license_url or "").strip() or None,
        )
    return out


# --------------------------------------------------------------------- 2026
def _load_final_entrants():
    """The frozen 26-prospect holdout board — read untouched, never
    recomputed. Returns {canonical_prospect_id: {...}}."""
    from paths import interim

    pred_path = ROOT / "data" / "processed" / "2026" / "draftlens_2026_predictions.parquet"
    comp_path = ROOT / "data" / "processed" / "2026" / "draftlens_2026_comparables.json"
    if not (pred_path.exists() and comp_path.exists()):
        return {}, None

    import replay
    replay._require_frozen_predictions()  # refuse to export a tampered artifact

    predictions = pd.read_parquet(pred_path)
    comparables = json.loads(comp_path.read_text())
    feats = pd.read_parquet(interim("features") / "features_2026.parquet") \
        .set_index("canonical_prospect_id")

    out = {}
    for _, row in predictions.iterrows():
        pid = row.canonical_prospect_id
        feats_row = feats.loc[pid]
        out[pid] = dict(
            name=row.player_name, school=row.college, position=row.position_3,
            board=_board(row), stats=_stats(feats_row),
            dimensions=_dimensions(row), profiles=_profiles(row),
            coverage=_r3(row.team_need_data_coverage),
            comparables=_comparables(pid, comparables))

    provenance_path = ROOT / "data" / "processed" / "2026" / "replay_provenance.json"
    provenance = json.loads(provenance_path.read_text()) if provenance_path.exists() else None
    return out, provenance


def _load_all_declared():
    """The larger ALL-DECLARED product board — additional exploration
    generated after the holdout. Returns ({canonical_prospect_id: {...}},
    insufficient_data_records, audit)."""
    import declared

    if not (declared.DECLARED_PREDICTIONS_PATH.exists()
           and declared.DECLARED_FEATURES_PATH.exists()):
        return {}, [], None

    predictions = pd.read_parquet(declared.DECLARED_PREDICTIONS_PATH)
    feats = pd.read_parquet(declared.DECLARED_FEATURES_PATH) \
        .set_index("canonical_prospect_id")
    comparables = (json.loads(declared.DECLARED_COMPARABLES_PATH.read_text())
                  if declared.DECLARED_COMPARABLES_PATH.exists() else {})
    insufficient = (json.loads(declared.DECLARED_INSUFFICIENT_PATH.read_text())
                    if declared.DECLARED_INSUFFICIENT_PATH.exists() else [])
    audit = (json.loads(declared.DECLARED_PROVENANCE_PATH.read_text()).get("audit")
            if declared.DECLARED_PROVENANCE_PATH.exists() else None)

    out = {}
    for _, row in predictions.iterrows():
        pid = row.canonical_prospect_id
        feats_row = feats.loc[pid]
        out[pid] = dict(
            name=row.player_name, school=row.college, position=row.position_3,
            populationStatus=row.population_status,
            board=_board(row), stats=_stats(feats_row),
            dimensions=_dimensions(row), profiles=_profiles(row),
            coverage=_r3(row.team_need_data_coverage),
            comparables=_comparables(pid, comparables))
    return out, insufficient, audit


def build_year_2027():
    """The 2027 Projected Watchlist — NOT an official declaration list.
    Returns status "unavailable" if no source data has been acquired, or
    "watchlist" with returning/incoming prospects otherwise. Never includes a
    board, Draft Probability, or Overall Score for any 2027 prospect."""
    import watchlist2027

    if not watchlist2027.SOURCES_PATH.exists():
        return dict(status="unavailable",
                   reason="No official 2027 NBA early-entry declarations "
                         "exist yet, and no projected watchlist source data "
                         "has been acquired.")

    provenance = (json.loads(watchlist2027.PROVENANCE_PATH.read_text())
                 if watchlist2027.PROVENANCE_PATH.exists() else None)
    if provenance is None:
        return dict(status="unavailable",
                   reason="2027 watchlist source data present but not yet "
                         "built — run scripts/build.py watchlist-2027")

    incoming = (json.loads(watchlist2027.INCOMING_PATH.read_text())
               if watchlist2027.INCOMING_PATH.exists() else [])
    photos = _load_photo_index()
    prospects = []
    for r in incoming:
        pid = r["canonical_prospect_id"]
        prospects.append(dict(
            id=pid, name=r["player_name"],
            school=r["college"], classYear=_clean_str(r.get("class_year")),
            photo=photos.get(pid),
            hasStats=False, stats=None, dimensions=None, profiles=None,
            coverage=None, comparables=[]))

    if watchlist2027.RETURNING_PREDICTIONS_PATH.exists():
        predictions = pd.read_parquet(watchlist2027.RETURNING_PREDICTIONS_PATH)
        comparables = (json.loads(watchlist2027.RETURNING_COMPARABLES_PATH.read_text())
                      if watchlist2027.RETURNING_COMPARABLES_PATH.exists() else {})
        for _, row in predictions.iterrows():
            pid = row.canonical_prospect_id
            prospects.append(dict(
                id=pid, name=row.player_name, school=row.college,
                classYear=_clean_str(row.get("class_year")), hasStats=True,
                photo=photos.get(pid),
                stats=_stats(row), dimensions=_dimensions(row),
                profiles=_profiles(row), coverage=_r3(row.team_need_data_coverage),
                comparables=_comparables(pid, comparables)))

    prospects.sort(key=lambda p: p["name"])
    return dict(
        status="watchlist",
        label=provenance["label"],
        consensusRule=provenance["consensus_rule"],
        sources=provenance["sources"],
        prospectCount=provenance["watchlist_size"],
        returningCount=provenance["returning"],
        incomingCount=provenance["incoming"],
        prospects=prospects,
    )


def _official_source(year=YEAR):
    from data.wikipedia import DECLARED_SNAPSHOTS
    snap = DECLARED_SNAPSHOTS.get(year)
    if snap is None:
        return None
    return dict(name="NBA official early-entry candidate announcement",
               url=snap["canonical_url"], announcementDate=snap["announcement_date"],
               note=snap["note"])


def build_year_2026():
    final_entrants, replay_provenance = _load_final_entrants()
    all_declared, insufficient, audit = _load_all_declared()
    if not final_entrants:
        return dict(status="unavailable",
                   reason="2026 holdout replay artifacts not found — run "
                         "scripts/build.py replay-2026 then replay-2026-eval")

    photos = _load_photo_index()

    merged = {}
    for pid, rec in all_declared.items():
        merged[pid] = dict(
            id=pid, name=rec["name"], school=rec["school"], position=rec["position"],
            populationStatus=rec["populationStatus"],
            photo=photos.get(pid),
            finalEntrantsBoard=final_entrants[pid]["board"] if pid in final_entrants else None,
            declaredBoard=rec["board"],
            stats=rec["stats"], dimensions=rec["dimensions"],
            profiles=rec["profiles"], coverage=rec["coverage"],
            comparables=rec["comparables"])
    # Any FINAL_ENTRY prospect not present in the declared computation (e.g.
    # the declared-pool acquisition has not been run) still appears, using
    # only the frozen holdout data.
    for pid, rec in final_entrants.items():
        if pid in merged:
            continue
        merged[pid] = dict(
            id=pid, name=rec["name"], school=rec["school"], position=rec["position"],
            populationStatus="FINAL_ENTRY", photo=photos.get(pid),
            finalEntrantsBoard=rec["board"],
            declaredBoard=None, stats=rec["stats"], dimensions=rec["dimensions"],
            profiles=rec["profiles"], coverage=rec["coverage"],
            comparables=rec["comparables"])

    prospects = sorted(merged.values(),
                       key=lambda p: (p["finalEntrantsBoard"] is None,
                                     (p["finalEntrantsBoard"] or p["declaredBoard"])["rank"]))

    insufficient_out = [
        dict(id=r["canonical_prospect_id"], name=r["player_name"],
            school=r["college"], position=r.get("position"),
            populationStatus=r["population_status"])
        for r in insufficient
    ]

    out = dict(
        status="available",
        methodologyFreeze=(replay_provenance or {}).get("analytics_freeze_tag"),
        finalEntrantsCount=len(final_entrants),
        declaredCount=len(all_declared) + len(insufficient_out),
        scoreableDeclaredCount=len(all_declared),
        officialSource=_official_source(),
        audit=audit,
        prospects=prospects,
        insufficientDataProspects=insufficient_out,
    )
    return out


def _validation_summary(year_2026):
    """Aggregate, class-level validation numbers only — never a per-prospect
    2026 outcome. Safe for the About page per docs/VALIDATION.md."""
    out = {
        "historical": {
            "developmentPopulation": [887, 431, 456],
            "draftProbabilityMacroAuc": 0.6986,
            "draftOrderMacroSpearman": 0.2968,
            "generalBoardBinaryAuc": 0.7123,
            "generalBoardGradedNdcg": 0.8283,
        },
        "holdout2026": None,
        "noPostHoldoutTuning": True,
        "note": "Methodology was frozen (tag analytics-freeze-pre-2026) before "
               "the 2026 prediction freeze; predictions were hashed before "
               "any 2026 outcome was opened. The all-declared product board "
               "was generated separately, afterward, with the same frozen "
               "methodology — it was never part of the holdout evaluation. "
               "See docs/VALIDATION.md for the complete record.",
    }
    eval_path = ROOT / "data" / "processed" / "2026" / "replay_evaluation.json"
    if eval_path.exists():
        evaluation = json.loads(eval_path.read_text())
        gb = evaluation.get("general_board", {})
        support = evaluation.get("support", {})
        out["holdout2026"] = {
            "generalBoardGradedNdcg": gb.get("graded_ndcg"),
            "supportLabel": gb.get("support_label"),
            "draftedShare": support.get("drafted_share"),
        }
    return out


def build_payload():
    """Assemble the full export in memory. Pure function of the frozen
    artifacts already on disk — reads nothing else, computes nothing new."""
    year_2026 = build_year_2026()
    payload = {
        "version": "2026.1",
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "years": {
            "2026": year_2026,
            "2027": build_year_2027(),
        },
        "teamNeedProfiles": list(PROFILE_KEYS.values()),
        "customDimensions": CUSTOM_DIMENSIONS,
        "methodologySummary": {
            "generalBoard": "Draft Probability × Draft Order quality, "
                           "combined into a 0-100 class-relative Overall Score.",
            "teamNeed": "NCAA peer-relative statistical trait scoring against "
                       "six factual dimensions. Not a prediction.",
            "comparables": "Normalized NCAA ↔ NBA statistical similarity "
                          "across six role dimensions. Descriptive resemblance "
                          "only, never a projection.",
            "validation": "Seven historical forward-in-time folds (2019-2025), "
                         "plus one final 2026 holdout replay.",
        },
        "validationSummary": _validation_summary(year_2026),
    }
    return payload


def _to_camel(key):
    parts = key.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


def assert_no_leakage(payload):
    """Recursively scan the finished payload for any prohibited field name,
    at any nesting depth, under any of its snake_case/camelCase spellings."""
    bad = []

    def walk(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                key_norm = k.lower().replace("_", "")
                for prohibited in PROHIBITED_FIELDS:
                    if key_norm == prohibited.lower().replace("_", ""):
                        bad.append(f"{path}.{k}")
                walk(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")

    walk(payload, "$")
    if bad:
        raise AssertionError(f"target field(s) present in app export: {bad}")


def write_payload(payload=None, path=APP_DATA_PATH):
    payload = payload if payload is not None else build_payload()
    assert_no_leakage(payload)

    path.parent.mkdir(parents=True, exist_ok=True)
    # Stable, deterministic serialization: sorted keys, fixed separators, no
    # trailing whitespace, so the same frozen inputs always produce the same
    # bytes and the same hash.
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
    path.write_text(text + "\n")

    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    n = len(payload["years"].get("2026", {}).get("prospects", []))
    return path, digest, n
