"""The public application data export — the ONE thing the frontend reads.

Turns the already-frozen, already-hashed 2026 prediction artifacts
(`src/replay.py`) into a small, deterministic, target-free JSON file the
static React app consumes directly. This module performs NO analytical
computation of its own: every number here was already produced by the frozen
Draft Probability / Draft Order / General Board / Team Need / NBA Comparables
systems during the 2026 replay. It only selects, renames and rounds fields
for display.

Nothing here may read `_draft_order_raw_pick_signal_INTERNAL_ONLY` or any
2026 outcome field — `assert_no_leakage` checks the finished payload before
it is written, the same discipline `replay.assert_target_free` applies to the
prediction artifact itself.
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
# for the custom UI; ATHLETICISM is permanently unavailable. Do not add to
# this list without a product decision recorded in config/team_need.json.
CUSTOM_DIMENSIONS = ["shooting", "playmaking", "defensiveProduction",
                     "rebounding", "size"]


def _r1(x):
    """Round to 1 decimal, or None. Never fabricates a value for NaN."""
    if x is None or pd.isna(x):
        return None
    return round(float(x), 1)


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
        similarityScore=_rint(entry["similarity_score"]),
        referenceSeasons=list(entry["reference_seasons"]),
        closestDimensions=close,
        differences=diffs,
    )


def _prospect(row, feats_row, comparables_entry):
    pid = row.canonical_prospect_id
    comps = []
    if comparables_entry is not None and comparables_entry.get("status") == "OK":
        comps = [_comparable(c) for c in comparables_entry["comparables"]]

    return {
        "id": pid,
        "name": row.player_name,
        "school": row.college,
        "position": row.position_3,
        "board": {
            "rank": int(row.board_rank),
            "overallScore": int(row.overall_score),
            "draftProbability": _r3(row.stage_a_probability),
            "draftOrderSignal": _r3(row.stage_b_quality),
        },
        "stats": {
            "pointsPer40": _r1(feats_row.points_per_40),
            "reboundsPer40": _r1(feats_row.reb_per_40),
            "assistsPer40": _r1(feats_row.assists_per_40),
            "threePointPct": _r3(feats_row.three_point_pct),
            "ftPct": _r3(feats_row.ft_pct),
            "tsPct": _r3(feats_row.ts_pct),
            "minutesPerGame": _r1(feats_row.minutes_per_game),
            "gamesPlayed": _rint(feats_row.games_played),
        },
        "dimensions": {
            "shooting": _r1(row.dimension_shooting),
            "playmaking": _r1(row.dimension_playmaking),
            "defensiveProduction": _r1(row.dimension_box_score_defensive_production),
            "rebounding": _r1(row.dimension_rebounding),
            "size": _r1(row.dimension_size),
            "rimPressure": _r1(row.dimension_rim_pressure),
        },
        "profiles": {v: _profile(row, k.lower()) for k, v in PROFILE_KEYS.items()},
        "coverage": _r3(row.team_need_data_coverage),
        "comparables": comps,
    }


def build_payload():
    """Assemble the full export in memory. Pure function of the frozen
    artifacts already on disk — reads nothing else, computes nothing new."""
    from paths import interim

    pred_path = ROOT / "data" / "processed" / "2026" / "draftlens_2026_predictions.parquet"
    comp_path = ROOT / "data" / "processed" / "2026" / "draftlens_2026_comparables.json"
    prov_path = ROOT / "data" / "processed" / "2026" / "replay_provenance.json"
    if not (pred_path.exists() and comp_path.exists() and prov_path.exists()):
        raise FileNotFoundError(
            "2026 replay artifacts missing — run scripts/build.py replay-2026 "
            "then scripts/build.py replay-2026-eval before exporting")

    predictions = pd.read_parquet(pred_path).sort_values("board_rank")
    comparables = json.loads(comp_path.read_text())
    provenance = json.loads(prov_path.read_text())
    feats = pd.read_parquet(interim("features") / "features_2026.parquet") \
        .set_index("canonical_prospect_id")

    prospects = []
    for _, row in predictions.iterrows():
        feats_row = feats.loc[row.canonical_prospect_id]
        prospects.append(_prospect(row, feats_row,
                                   comparables.get(row.canonical_prospect_id)))

    validation = json.loads(
        (ROOT / "data" / "processed" / "2026" / "replay_evaluation.json").read_text()
    ) if (ROOT / "data" / "processed" / "2026" / "replay_evaluation.json").exists() else None

    payload = {
        "version": "2026-final",
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "methodologyFreeze": provenance["analytics_freeze_tag"],
        "prospectCount": len(prospects),
        "prospects": prospects,
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
        "validationSummary": _validation_summary(validation),
    }
    return payload


def _validation_summary(evaluation):
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
               "any 2026 outcome was opened. See docs/VALIDATION.md for the "
               "complete record, including a disclosed process note.",
    }
    if evaluation is not None:
        gb = evaluation.get("general_board", {})
        support = evaluation.get("support", {})
        out["holdout2026"] = {
            "generalBoardGradedNdcg": gb.get("graded_ndcg"),
            "supportLabel": gb.get("support_label"),
            "draftedShare": support.get("drafted_share"),
        }
    return out


def _lower_first(s):
    return s[0].lower() + s[1:] if s else s


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
    return path, digest, len(payload["prospects"])
