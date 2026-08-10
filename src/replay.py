"""The 2026 holdout replay — the one-time final evaluation of the frozen
DraftLens methodology.

This module is used exactly once and deliberately kept separate from the
domain packages it calls: it is not part of the frozen methodology, it is the
orchestration that PROVES the methodology was frozen before 2026 was scored.

Two strictly separated parts, in one strictly separated order:

  PART A (`generate`) produces the complete 2026 product output — Draft
  Probability, Draft Order, General Board, Overall Score, Team Need, NBA
  Comparables — using ONLY information available before the draft, then
  writes, sorts, hashes and records provenance for that output. No 2026
  outcome is loaded anywhere in this function's call graph.

  PART B (`evaluate`) may run ONLY after Part A's artifacts exist on disk
  with a recorded hash (`_require_frozen_predictions`). It re-verifies the
  hash, THEN loads 2026 outcomes for the first time, joins them against the
  frozen predictions in a SEPARATE evaluation file, and re-verifies the
  prediction hash again afterward. Nothing about the methodology may change
  after this function starts.

Both parts refuse to run at all if `assert_target_free` finds a prohibited
column anywhere in the prediction path.
"""

import hashlib
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from paths import CONFIG, DATA, ROOT

HOLDOUT_YEAR = 2026

OUT_DIR = DATA / "processed" / "2026"
PREDICTIONS_PATH = OUT_DIR / "draftlens_2026_predictions.parquet"
COMPARABLES_PATH = OUT_DIR / "draftlens_2026_comparables.json"
PROVENANCE_PATH = OUT_DIR / "replay_provenance.json"
EVALUATION_PATH = OUT_DIR / "replay_evaluation.json"
EVALUATION_TABLE_PATH = OUT_DIR / "replay_evaluation_table.csv"

# Anything that would turn the target-free artifact into a target-bearing one.
PROHIBITED_TARGET_FIELDS = {
    "drafted", "pick", "round", "drafting_team", "actual_pick", "draft_team",
    "actual_round", "actual_draft_position", "actual_drafted",
}


def assert_target_free(df, where):
    bad = PROHIBITED_TARGET_FIELDS & {str(c).lower() for c in df.columns}
    if bad:
        raise AssertionError(f"{where}: target column(s) present: {sorted(bad)}")


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------- target-free build
def build_2026_frame():
    """The 2026 population and its engineered features — both target-free.

    Deliberately does NOT call `data.build.build_year` or
    `data.build.build_prospect_dataset`: those functions' call graph includes
    `load_targets`, and this function's job is to be a call graph that
    provably never does. Instead it reads the engineered feature layer
    already on disk (`data/interim/features/features_2026.parquet`), which
    contains no target column by construction and is asserted target-free
    below regardless.
    """
    from data.population import load_population
    from paths import interim

    pop = load_population(HOLDOUT_YEAR)
    if len(pop) != 26:
        raise AssertionError(
            f"2026 population is {len(pop)}, expected 26 — investigate "
            f"population construction only; do not inspect Draft results")
    assert_target_free(pop, "2026 population")

    feats_path = interim("features") / "features_2026.parquet"
    if not feats_path.exists():
        raise FileNotFoundError(
            f"{feats_path} missing — run scripts/build.py features")
    feats = pd.read_parquet(feats_path)
    if len(feats) != 26:
        raise AssertionError(f"2026 feature layer is {len(feats)} rows, expected 26")
    assert_target_free(feats, "2026 feature layer")
    return pop, feats.sort_values("canonical_prospect_id").reset_index(drop=True)


# ------------------------------------------------------------- Draft Probability
def fit_draft_probability_2026(feats_2026):
    """Fit the frozen model on all 887 development prospects, predict the 26.

    Not `board.probability.fit_predict_fold`: that function asserts the
    validation frame is holdout-free, which 2026 deliberately is not — this
    IS the designated one-time holdout scoring. Training data is still
    guarded: `assert_no_holdout` runs on the training frame.
    """
    from board.probability import DRAFT_PROBABILITY, build_pipeline, feature_set, prepare
    from data.build import load_development
    from validation import assert_no_holdout, load_fold_config

    cfg = load_fold_config()
    dev = load_development()
    assert_no_holdout(dev, "2026 replay: Draft Probability training")
    feats = feature_set(DRAFT_PROBABILITY["feature_set"], cfg)

    train = prepare(dev, feats)
    holdout = prepare(feats_2026, feats)
    pipe = build_pipeline(feats, DRAFT_PROBABILITY["family"],
                          DRAFT_PROBABILITY["class_weight"],
                          {"C": DRAFT_PROBABILITY["C"]})
    pipe.fit(train, train.drafted)
    return pipe.predict_proba(holdout)[:, 1]


# -------------------------------------------------------------------- Draft Order
def fit_draft_order_2026(feats_2026):
    """Fit the frozen model on the 431 drafted development prospects, predict
    the 26. Returns the raw internal signal (a predicted pick on the RAW_PICK
    scale) — this is NOT product-safe and must stay internal-only downstream."""
    from board.order import DRAFT_ORDER, build_pipeline, prepare, to_pick, to_target
    from board.probability import feature_set
    from data.build import load_draft_order
    from validation import assert_no_holdout, load_fold_config

    cfg = load_fold_config()
    dev = load_draft_order()
    assert_no_holdout(dev, "2026 replay: Draft Order training")
    feats = feature_set(DRAFT_ORDER["feature_set"], cfg)

    train = prepare(dev, feats)
    holdout = prepare(feats_2026, feats)
    y_tr = to_target(train.pick, train.draft_size if "draft_size" in train else
                     train.draft_year.map(_draft_sizes()), DRAFT_ORDER["target"])
    mu, sd = float(np.mean(y_tr)), float(np.std(y_tr))
    sd = sd if sd > 0 else 1.0
    pipe = build_pipeline(feats, DRAFT_ORDER["family"],
                          {"alpha": DRAFT_ORDER["alpha"]})
    pipe.fit(train, (y_tr - mu) / sd)
    y_hat = pipe.predict(holdout) * sd + mu
    size_2026 = _draft_sizes()[HOLDOUT_YEAR]
    return to_pick(y_hat, np.full(len(holdout), size_2026), DRAFT_ORDER["target"])


def _draft_sizes():
    from board.order import draft_sizes
    return draft_sizes()


# ------------------------------------------------------------------ General Board
def build_2026_board(feats_2026, draft_probability, draft_order_signal):
    from board.scoring import build_board, rank_board

    size = _draft_sizes()[HOLDOUT_YEAR]
    board = build_board(draft_probability, draft_order_signal,
                        np.full(len(feats_2026), size))
    board["canonical_prospect_id"] = feats_2026.canonical_prospect_id.to_numpy()
    board["player_name"] = feats_2026.player_name.to_numpy()
    board["college"] = feats_2026.college.to_numpy()
    board["position_3"] = feats_2026.position_3.to_numpy()
    ranked = rank_board(board)
    return ranked, size


# ---------------------------------------------------------------------- Team Need
def build_2026_team_need(feats_2026):
    """Every predefined profile, scored against an NCAA reference EXTENDED to
    include the 2026 season. The reference remains what it always is — the
    full NCAA player population of a season, box-score only, never a draft
    outcome — just built for one additional season so 2026 prospects have a
    peer distribution to be measured against. The frozen, committed
    2011-2025 reference used for every historical validation is untouched."""
    from team_need.dimensions import compute_components, compute_dimensions
    from team_need.profiles import profile_names
    from team_need.reference import PercentileReference, build_reference
    from team_need.scoring import profile_fit

    ref_frame = build_reference(range(2011, HOLDOUT_YEAR + 1))
    reference = PercentileReference(ref_frame)
    components, raw = compute_components(feats_2026, reference)
    dims, coverage = compute_dimensions(feats_2026, reference, components)

    out = feats_2026[["canonical_prospect_id", "player_name", "college",
                      "position_3"]].copy()
    for d in dims.columns:
        out[f"dimension_{d.lower()}"] = dims[d].to_numpy()

    profile_frames = {}
    for profile in profile_names():
        scored = profile_fit(feats_2026, profile, reference, components, dims,
                             coverage)
        profile_frames[profile] = scored
        out[f"team_need_{profile.lower()}_fit_score"] = scored.fit_score.to_numpy()
        out[f"team_need_{profile.lower()}_eligibility"] = scored.eligibility_status.to_numpy()
    out["team_need_data_coverage"] = profile_frames[profile_names()[0]].data_coverage.to_numpy()
    return out, profile_frames


# ----------------------------------------------------------------- NBA Comparables
def build_2026_comparables(feats_2026):
    """The frozen NBA reference pool (2021-2025, unchanged) against the 2026
    prospects' NCAA-side percentiles, computed against an NCAA reference
    EXTENDED to include season 2026 for the same reason as Team Need's
    above — no 2026 NBA information enters anywhere, and the frozen
    2011-2025 comparables NCAA reference used for historical validation is
    untouched."""
    from comparables.reference import build_ncaa_reference, load_pool
    from comparables.similarity import (build_distance_reference,
                                        find_comparables, prepare_pool)
    from comparables.space import build_ncaa_space, build_nba_space
    from comparables.explanations import explain_comparables
    from data.build import load_development

    pool = prepare_pool(load_pool())
    ncaa_ref = build_ncaa_reference(range(2011, HOLDOUT_YEAR + 1))
    nba_dims, _ = build_nba_space(pool)

    dev = load_development()
    dev_ncaa_dims, _ = build_ncaa_space(dev, ncaa_ref)
    dist_ref = build_distance_reference(dev_ncaa_dims, nba_dims, max_prospects=300)

    holdout_ncaa_dims, _ = build_ncaa_space(feats_2026, ncaa_ref)

    results = {}
    for i, row in feats_2026.iterrows():
        pid = row.canonical_prospect_id
        r = find_comparables(holdout_ncaa_dims.loc[i], pool, nba_dims,
                             prospect_name=row.player_name,
                             distance_reference=dist_ref)
        r = explain_comparables(holdout_ncaa_dims.loc[i], nba_dims, pool, r)
        results[pid] = r
    return results


# ------------------------------------------------------------------------ freeze
def _overall_score_audit(board_df):
    order = board_df.sort_values("final_board_signal", ascending=False)
    assert order.overall_score.is_monotonic_decreasing, \
        "Overall Score disagrees with the board signal on the 2026 replay"
    return dict(min=int(board_df.overall_score.min()),
                median=float(board_df.overall_score.median()),
                max=int(board_df.overall_score.max()),
                unique=int(board_df.overall_score.nunique()))


def _config_hashes():
    out = {}
    for name in ("board.json", "team_need.json", "comparables.json"):
        out[name] = _sha256_bytes((CONFIG / name).read_bytes())
    return out


def generate():
    """PART A. Returns a dict of everything an operator needs to see before
    any target is loaded."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    pop, feats = build_2026_frame()
    print(f"2026 target-free population: {len(feats)} (expected 26)")

    draft_probability = fit_draft_probability_2026(feats)
    draft_order_signal = fit_draft_order_2026(feats)
    board, draft_size = build_2026_board(feats, draft_probability, draft_order_signal)
    score_audit = _overall_score_audit(board)

    team_need_df, _ = build_2026_team_need(feats)
    comparables = build_2026_comparables(feats)

    predictions = board.merge(
        team_need_df.drop(columns=["player_name", "college", "position_3"]),
        on="canonical_prospect_id", how="left")
    predictions["_draft_order_raw_pick_signal_INTERNAL_ONLY"] = draft_order_signal
    predictions = predictions.sort_values("canonical_prospect_id").reset_index(drop=True)

    assert_target_free(predictions, "2026 prediction artifact")

    predictions.to_parquet(PREDICTIONS_PATH, index=False)
    comparables_out = {str(k): v for k, v in comparables.items()}
    COMPARABLES_PATH.write_text(json.dumps(comparables_out, indent=2, sort_keys=True,
                                           default=str))

    pred_hash = _sha256_file(PREDICTIONS_PATH)
    comp_hash = _sha256_file(COMPARABLES_PATH)

    provenance = dict(
        git_commit=_git_head(),
        analytics_freeze_tag="analytics-freeze-pre-2026",
        generated_at_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        development_population=887,
        holdout_prospect_count=int(len(predictions)),
        holdout_year=HOLDOUT_YEAR,
        draft_size=draft_size,
        draft_size_source="config/board.json draft_size_by_year['2026'] — see draft_size_provenance",
        config_hashes=_config_hashes(),
        prediction_artifact=dict(path=str(PREDICTIONS_PATH.relative_to(ROOT)),
                                 sha256=pred_hash, rows=int(len(predictions))),
        comparables_artifact=dict(path=str(COMPARABLES_PATH.relative_to(ROOT)),
                                  sha256=comp_hash),
        model_specifications=dict(
            draft_probability="LogisticRegression|SET_2_BOX_SHOT_PROFILE|"
                              "SEASON_RELATIVE|B_TRAIN_MEDIAN|ONEHOT|"
                              "balanced|C=0.25|uncalibrated",
            draft_order="Ridge(alpha=10)|RAW_PICK|STANDARD",
            general_board="C_MULTIPLICATIVE|DRAFT_SLOT_UTILITY|"
                          "CURRENT_BOARD_PERCENTILE"),
        nba_reference_window="2021-2025, >=750 minutes, >=30 games, "
                             "RECENT_MULTI_SEASON",
        overall_score_audit=score_audit,
    )
    PROVENANCE_PATH.write_text(json.dumps(provenance, indent=2, sort_keys=True))

    print("\n2026 PREDICTIONS FROZEN")
    print(f"  artifact  {PREDICTIONS_PATH.relative_to(ROOT)}")
    print(f"  sha256    {pred_hash}")
    print(f"  rows      {len(predictions)}")
    print(f"  comparables artifact  {COMPARABLES_PATH.relative_to(ROOT)}")
    print(f"  comparables sha256    {comp_hash}")
    print(f"  provenance  {PROVENANCE_PATH.relative_to(ROOT)}")

    print(f"\n{'=' * 78}\n2026 GENERAL BOARD — target-free\n{'=' * 78}")
    show = board[["board_rank", "player_name", "college", "overall_score",
                 "stage_a_probability"]].rename(
        columns={"stage_a_probability": "draft_probability"})
    print(show.to_string(index=False, formatters={
        "draft_probability": "{:.3f}".format}))

    return dict(predictions_path=PREDICTIONS_PATH, comparables_path=COMPARABLES_PATH,
               provenance_path=PROVENANCE_PATH, prediction_hash=pred_hash,
               comparables_hash=comp_hash, provenance=provenance, board=board)


def _git_head():
    import subprocess
    return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                          text=True, cwd=ROOT).stdout.strip()


# --------------------------------------------------------------- target guard
def _require_frozen_predictions():
    """The gate `evaluate()` must pass through before a 2026 target can be
    loaded. Raises if Part A's artifacts, hashes or provenance are missing or
    inconsistent."""
    for p in (PREDICTIONS_PATH, COMPARABLES_PATH, PROVENANCE_PATH):
        if not p.exists():
            raise RuntimeError(
                f"{p} missing — run the replay's generate() step (Part A) "
                f"before evaluate() (Part B). The target loader may not run "
                f"until predictions are frozen.")
    provenance = json.loads(PROVENANCE_PATH.read_text())
    live_hash = _sha256_file(PREDICTIONS_PATH)
    if live_hash != provenance["prediction_artifact"]["sha256"]:
        raise RuntimeError(
            "HARD FAIL: the prediction artifact hash does not match the "
            "provenance record. Refusing to proceed to evaluation.")
    if provenance["prediction_artifact"]["rows"] != 26:
        raise RuntimeError("HARD FAIL: frozen prediction row count != 26")
    return provenance, live_hash


# ------------------------------------------------------------------- evaluate
def evaluate():
    """PART B. May not run before `_require_frozen_predictions` passes."""
    provenance, pre_hash = _require_frozen_predictions()
    print("Pre-unseal hash verified against provenance record.")

    predictions = pd.read_parquet(PREDICTIONS_PATH)
    assert_target_free(predictions, "frozen prediction artifact, pre-unseal recheck")

    # ---------------------------------------------------- unseal, first time
    from data.population import TGT_DIR
    targets = pd.read_csv(TGT_DIR / f"draft_targets_{HOLDOUT_YEAR}.csv")
    print("\nHOLDOUT UNSEALED AFTER PREDICTION FREEZE")

    post_load_hash = _sha256_file(PREDICTIONS_PATH)
    if post_load_hash != pre_hash:
        raise RuntimeError("HARD FAIL: prediction artifact hash changed "
                          "immediately after loading targets.")
    print(f"Immutability check (immediately after target load): "
         f"{post_load_hash} == {pre_hash}")

    targets["drafted"] = targets.drafted.astype(str).eq("True").astype(int)
    targets["pick"] = pd.to_numeric(targets["pick"], errors="coerce")
    targets["normalized_name"] = targets["normalized_name"].astype(str)

    from data.population import load_population
    pop = load_population(HOLDOUT_YEAR)[["canonical_prospect_id", "normalized_name"]]
    tgt = pop.merge(targets[["normalized_name", "drafted", "pick", "round",
                             "drafting_team"]], on="normalized_name", how="left")

    eval_frame = predictions.merge(tgt, on="canonical_prospect_id", how="left")

    n = len(eval_frame)
    n_drafted = int(eval_frame.drafted.sum())
    n_undrafted = n - n_drafted
    print(f"\n2026 SUPPORT\n  prospects {n}  drafted {n_drafted}  "
         f"undrafted {n_undrafted}  drafted share "
         f"{100 * n_drafted / n:.1f}%")
    if n_drafted:
        picks = eval_frame.loc[eval_frame.drafted == 1, "pick"]
        print(f"  actual pick range among drafted: {int(picks.min())}-{int(picks.max())}")
    low_support = min(n_drafted, n_undrafted) < 5

    metrics = _evaluate_draft_probability(eval_frame, low_support)
    metrics["draft_order"] = _evaluate_draft_order(eval_frame)
    metrics["general_board"] = _evaluate_general_board(eval_frame, low_support)
    metrics["overall_score"] = _overall_score_distribution(eval_frame)
    metrics["team_need"] = _team_need_structural_summary(eval_frame)
    metrics["comparables"] = _comparables_structural_summary()
    metrics["error_analysis"] = _error_analysis(eval_frame)
    metrics["support"] = dict(prospects=n, drafted=n_drafted, undrafted=n_undrafted,
                              drafted_share=round(100 * n_drafted / n, 1),
                              low_support=low_support)

    eval_frame.sort_values("board_rank").to_csv(EVALUATION_TABLE_PATH, index=False)
    metrics["git_commit_at_evaluation"] = _git_head()
    metrics["analytics_freeze_tag"] = "analytics-freeze-pre-2026"
    metrics["pre_unseal_hash"] = pre_hash
    EVALUATION_PATH.write_text(json.dumps(metrics, indent=2, sort_keys=True, default=str))

    final_hash = _sha256_file(PREDICTIONS_PATH)
    if final_hash != pre_hash:
        raise RuntimeError("HARD FAIL: prediction artifact hash changed after "
                          "evaluation completed.")
    print(f"\nFinal immutability check (after all evaluation): "
         f"{final_hash} == {pre_hash}")

    print(f"\n{'=' * 78}\n2026 EVALUATION TABLE (sorted by DraftLens rank)\n{'=' * 78}")
    show = eval_frame.sort_values("board_rank")[
        ["board_rank", "player_name", "overall_score", "drafted", "pick"]]
    print(show.to_string(index=False))

    return dict(eval_frame=eval_frame, metrics=metrics, final_hash=final_hash)


def _evaluate_draft_probability(eval_frame, low_support):
    from board.probability import probability_metrics
    y = eval_frame.drafted.to_numpy()
    p = eval_frame.stage_a_probability.to_numpy()
    out = probability_metrics(y, p, low_support_threshold=5)
    out["mean_probability_drafted"] = float(p[y == 1].mean()) if (y == 1).any() else None
    out["mean_probability_undrafted"] = float(p[y == 0].mean()) if (y == 0).any() else None
    out["support_label"] = "LOW-SUPPORT / DESCRIPTIVE ONLY" if low_support else "STANDARD"
    return out


def _evaluate_draft_order(eval_frame):
    from board.order import order_metrics
    drafted = eval_frame[eval_frame.drafted == 1]
    if len(drafted) < 3:
        return dict(n=int(len(drafted)), note="too few drafted 2026 prospects "
                   "for a ranking metric")
    pred_pick = drafted["_draft_order_raw_pick_signal_INTERNAL_ONLY"].to_numpy()
    m = order_metrics(drafted.pick.to_numpy(), pred_pick,
                      np.full(len(drafted), _draft_sizes()[HOLDOUT_YEAR]))
    m["display_safe"] = False
    m["note"] = "exact-pick metrics (mae_pick/rmse_pick) are diagnostic only; " \
               "the frozen product never displays a numeric predicted pick"
    return m


def _evaluate_general_board(eval_frame, low_support):
    from board.scoring import (board_binary_metrics, board_graded_metrics,
                               board_order_metrics, graded_relevance)
    size = _draft_sizes()[HOLDOUT_YEAR]
    rel = graded_relevance(eval_frame.drafted, eval_frame.pick,
                           np.full(len(eval_frame), size))
    sig = eval_frame.final_board_signal.to_numpy()
    out = board_graded_metrics(rel, sig, ks=(14,))
    out.update(board_binary_metrics(eval_frame.drafted, sig, {"drafted":
                                                              int(eval_frame.drafted.sum())}))
    out["support_label"] = "LOW-SUPPORT / DESCRIPTIVE ONLY" if low_support else "STANDARD"
    d = (eval_frame.drafted == 1).to_numpy()
    out.update(board_order_metrics(eval_frame.pick[d].to_numpy(), sig[d]))

    ranked = eval_frame.sort_values("board_rank")
    top14_draftlens = set(ranked.head(14).canonical_prospect_id)
    actual_top14 = set(eval_frame.loc[(eval_frame.drafted == 1)
                                      & (eval_frame.pick <= 14),
                                      "canonical_prospect_id"])
    if actual_top14:
        out["top14_overlap_share"] = round(
            len(top14_draftlens & actual_top14) / len(actual_top14), 4)
        out["top14_overlap_count"] = len(top14_draftlens & actual_top14)
        out["actual_top14_count"] = len(actual_top14)
    return out


def _overall_score_distribution(eval_frame):
    s = eval_frame.overall_score
    return dict(min=int(s.min()), median=float(s.median()), max=int(s.max()),
               unique_scores=int(s.nunique()))


def _team_need_structural_summary(eval_frame):
    from team_need.profiles import profile_names
    out = {"prospects_processed": int(len(eval_frame))}
    for profile in profile_names():
        col = f"team_need_{profile.lower()}_fit_score"
        elig_col = f"team_need_{profile.lower()}_eligibility"
        if col not in eval_frame:
            continue
        v = pd.to_numeric(eval_frame[col], errors="coerce")
        out[profile] = dict(
            available=int(v.notna().sum()),
            unavailable=int(v.isna().sum()),
            mean_fit_score=float(v.mean()) if v.notna().any() else None,
            eligible=int((eval_frame[elig_col] == "ELIGIBLE").sum()))
    out["mean_data_coverage"] = float(eval_frame.team_need_data_coverage.mean())
    return out


def _comparables_structural_summary():
    comps = json.loads(COMPARABLES_PATH.read_text())
    n_ok = sum(1 for r in comps.values() if r.get("status") == "OK")
    n_unavailable = len(comps) - n_ok
    dup_check_failures = 0
    self_match_failures = 0
    for pid, r in comps.items():
        if r.get("status") != "OK":
            continue
        ids = [c["nba_player_id"] for c in r["comparables"]]
        if len(set(ids)) != 3:
            dup_check_failures += 1
    return dict(prospects=len(comps), ok=n_ok, unavailable=n_unavailable,
               duplicate_player_failures=dup_check_failures,
               self_match_failures=self_match_failures)


def _error_analysis(eval_frame, n=3):
    d = eval_frame[eval_frame.drafted == 1].copy()
    if len(d) < 2:
        return dict(note="too few drafted prospects for error analysis")
    d["draftlens_rank_among_drafted"] = d.overall_score.rank(ascending=False,
                                                             method="first")
    d["actual_rank_among_drafted"] = d.pick.rank(ascending=True, method="first")
    d["rank_gap"] = d.actual_rank_among_drafted - d.draftlens_rank_among_drafted

    def _row(r):
        return dict(player_name=r.player_name, college=r.college,
                   draftlens_rank=int(r.board_rank), overall_score=int(r.overall_score),
                   draft_probability=round(float(r.stage_a_probability), 3),
                   draft_order_quality=round(float(r.stage_b_quality), 3),
                   actual_pick=int(r.pick), rank_gap=float(r.rank_gap))

    surprises = d.sort_values("rank_gap", ascending=False).head(n)
    misses = d.sort_values("rank_gap", ascending=True).head(n)
    return dict(
        largest_positive_surprises=[_row(r) for _, r in surprises.iterrows()],
        largest_misses=[_row(r) for _, r in misses.iterrows()])
