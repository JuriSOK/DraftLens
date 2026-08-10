"""Leakage rules, the temporal validation protocol, and shared validation
guards — the one place every domain's validator gets its assertions from.

THREE THINGS LIVE HERE, DELIBERATELY TOGETHER:

  LEAKAGE DEFINITIONS. What may never become a DraftLens feature. Two related
  but DIFFERENT policies:

    FEATURE-FILE POLICY  (`DENY_EXACT`, `DENY_SUBSTRING`, `SUSPICIOUS`)
        Columns that must never be WRITTEN into a feature file at all.
        Enforced when the prospect dataset is built (`data.build`).

    MODEL-INPUT POLICY  (`DENIED`, `DENIED_SUBSTR`)
        Columns that may exist in a feature file as identity/audit metadata but
        must never enter a model. Broader than the file policy: it also
        excludes identity keys, target fields, and audit columns that are
        legitimately stored but outcome-correlated.

  Several entries leak because their AVAILABILITY or GRANULARITY is decided by
  the outcome, not their values. Date of birth is 100% present for drafted and
  69% for undrafted prospects; `position_from_population` resolves to a
  five-position label for 100% of drafted versus 7.7% of undrafted. A
  missingness indicator for either would be the most target-predictive column
  in the dataset while carrying no basketball information.

  TEMPORAL PROTOCOL. Random train/test splitting is PROHIBITED for evaluation:
  it would place same-year prospects on both sides of a split and destroy the
  temporal guarantee. Every fold trains on draft years strictly earlier than
  the year it validates, and 2026 is a sealed holdout that must reach no fold,
  no fit and no artifact.

  SHARED GUARDS. `Guard` and the `check_*` helpers below were once duplicated
  across every phase validator; consolidating them means a guard is
  strengthened once and every domain benefits.

Changing a deny list, a fold boundary, or the holdout year requires an explicit
decision in docs/METHODOLOGY.md, not a code edit.

  ./.venv/bin/python scripts/validate.py
"""

import json
import subprocess

import pandas as pd

from paths import CONFIG, ROOT

# --------------------------------------------------------- feature-file policy
DENY_EXACT = {
    "drafted", "pick", "round", "drafting_team", "early_entrant",
    "population_source", "date_of_birth", "age", "current_age", "dob",
    "dob_missing", "draft_year_pick", "nba_player_id", "nba_athlete_id",
    "mock_rank", "consensus_rank", "analyst_rank", "green_room",
    "draft_selection", "draft_round",
    # dual-source metadata whose granularity/availability is decided by the
    # outcome itself. Drafted players inherit these from the DRAFT RESULTS
    # table, undrafted ones from the early-entrant list, so the label format
    # encodes the target.
    "position_from_population", "class_from_population",
    # pipeline metadata: every UNMATCHED prospect is undrafted
    "match_method", "match_confidence",
}

DENY_SUBSTRING = ("nba_", "_nba", "mock", "consensus", "analyst", "greenroom",
                  "postdraft", "post_draft", "outcome")

SUSPICIOUS = ("draft", "nba", "pick", "round", "rank", "future", "outcome",
              "target")

# Reviewed and allowed despite matching SUSPICIOUS: identity/context only.
SUSPICIOUS_ALLOWED = {"draft_year"}


# --------------------------------------------------------- model-input policy
DENIED = {
    # targets
    "drafted", "pick", "round", "drafting_team",
    # outcome-correlated metadata
    "early_entrant", "population_source", "position_from_population",
    "class_from_population", "match_method", "match_confidence",
    # age / DOB — availability is a function of the outcome
    "date_of_birth", "age", "current_age", "dob",
    # identity keys
    "canonical_prospect_id", "player_name", "normalized_name", "college",
    "wikipedia_title", "hoopr_athlete_id", "draft_year",
    # audit-only columns
    "shot_fga_coverage_ratio", "n_teams", "experience_years",
}

# `jump_shot` is excluded because the hoopR shot subcategories are not
# comparable across the 2020/21 schema break.
DENIED_SUBSTR = ("jump_shot", "nba_", "mock", "consensus", "analyst")


def denied_columns(columns):
    """Columns from `columns` that must never enter a model. Exact names match
    exactly; only DENIED_SUBSTR matches as a substring — substring-matching
    DENIED would flag legitimate features such as `usage_pct` (it contains
    "age")."""
    return [c for c in columns
            if c in DENIED or any(s in str(c).lower() for s in DENIED_SUBSTR)]


def assert_features_safe(columns, where=""):
    bad = denied_columns(columns)
    if bad:
        raise AssertionError(f"denied features{' in ' + where if where else ''}: {bad}")
    return list(columns)


# ------------------------------------------------------------- temporal protocol
HOLDOUT_YEAR = 2026
LOW_SUPPORT_YEAR = 2025   # Draft Probability: 26 drafted / 2 undrafted

FOLD_CONFIG = CONFIG / "board.json"


def load_fold_config(path=FOLD_CONFIG):
    """The frozen fold / feature-set configuration shared by every board
    component."""
    return json.loads(path.read_text())


def folds(cfg=None):
    """(fold_id, train_years, validate_year) tuples.

    Training is always strictly earlier than validation, and 2026 can appear on
    neither side. Both properties are asserted here rather than trusted.
    """
    cfg = cfg if cfg is not None else load_fold_config()
    out = []
    for f in cfg["folds"]:
        lo, hi = f["train"]
        vy = f["validate"]
        tr = list(range(lo, hi + 1))
        assert max(tr) < vy, "training years must precede the validation year"
        assert vy != HOLDOUT_YEAR and HOLDOUT_YEAR not in tr
        out.append((f["fold"], tr, vy))
    return out


def assert_no_holdout(df, where=""):
    """Hard guard: the 2026 holdout must never reach training or evaluation.

    Raises rather than warns. A silently-included holdout year would invalidate
    the single evaluation the holdout exists to provide.
    """
    if HOLDOUT_YEAR in set(pd.Series(df["draft_year"]).unique()):
        raise AssertionError(f"HOLDOUT GUARD: {HOLDOUT_YEAR} reached {where}")
    return df


# ------------------------------------------------------------------ guards
# Frozen population anchor. If a refactor or data refresh moves this, the
# science changed and the affected phase must be re-derived, not tolerated.
DEVELOPMENT_POPULATION = (887, 431, 456)      # rows, drafted, undrafted
UNRESOLVED_PROSPECTS = 8                       # all undrafted


class Guard:
    """Collects failures instead of raising, so one run reports every problem."""

    def __init__(self):
        self.failures, self.warnings = [], []

    def check(self, cond, msg, hard=True):
        if cond:
            return True
        (self.failures if hard else self.warnings).append(msg)
        print(f"  {'FAIL' if hard else 'WARN'}  {msg}")
        return False

    def report(self):
        print(f"\n{'=' * 78}\nRESULT\n{'=' * 78}")
        print(f"  hard failures: {len(self.failures)}\n"
              f"  warnings     : {len(self.warnings)}")
        for m in self.failures:
            print(f"   FAIL {m}")
        for m in self.warnings:
            print(f"   WARN {m}")
        return 1 if self.failures else 0


def check_holdout_absent(g, frames, where=""):
    """`frames`: {label: dataframe-or-iterable-of-years}."""
    for label, obj in frames.items():
        if isinstance(obj, pd.DataFrame):
            for col in ("draft_year", "validate_year"):
                if col in obj.columns:
                    vals = set(pd.to_numeric(obj[col], errors="coerce").dropna())
                    g.check(HOLDOUT_YEAR not in vals,
                            f"{label}: {HOLDOUT_YEAR} present in {col} {where}")
        else:
            g.check(HOLDOUT_YEAR not in set(obj),
                    f"{label}: {HOLDOUT_YEAR} present {where}")


def check_artifacts_holdout_free(g, out_dir):
    """No generated artifact may contain a holdout row, in any year column."""
    for p in sorted(out_dir.glob("*")):
        if p.suffix not in (".csv", ".parquet"):
            continue
        df = pd.read_csv(p, index_col=0) if p.suffix == ".csv" \
            else pd.read_parquet(p)
        for col in df.columns:
            if any(k in str(col).lower() for k in ("year", "season")):
                vals = pd.to_numeric(df[col], errors="coerce").dropna()
                g.check(HOLDOUT_YEAR not in set(vals),
                        f"{p.name}: {HOLDOUT_YEAR} in column {col}")


def check_source_never_loads_holdout(g, *paths):
    for path in paths:
        src = path.read_text()
        for banned in ("targets_2026", "features_2026", "predictions_2026"):
            g.check(banned not in src, f"{path.name} references {banned}")


def check_development_population(g, dev):
    n, nd, nu = len(dev), int(dev.drafted.sum()), int((dev.drafted == 0).sum())
    expected = DEVELOPMENT_POPULATION
    g.check((n, nd, nu) == expected,
            f"development population is {(n, nd, nu)}, expected {expected}")
    unresolved = int(dev.hoopr_athlete_id.isna().sum())
    g.check(unresolved >= UNRESOLVED_PROSPECTS,
            f"unresolved prospects lost ({unresolved} < {UNRESOLVED_PROSPECTS})")
    return unresolved


def check_features_safe(g, columns, where=""):
    bad = denied_columns(columns)
    g.check(not bad, f"denied features entered X{' (' + where + ')' if where else ''}: {bad}")


def check_fitted_model_clean(g, coef_index, extra_denied=frozenset()):
    """Compare on the BARE column name.

    DENIED holds exact names; substring-matching it would flag legitimate
    features such as `usage_pct`, which contains "age". Only DENIED_SUBSTR is a
    substring rule.
    """
    bare = [str(i).split("__", 1)[-1] for i in coef_index]
    bad = [n for n in bare if n in DENIED or n in extra_denied
           or any(s in n.lower() for s in DENIED_SUBSTR)]
    g.check(not bad, f"denied/target field in the fitted model: {bad}")


def check_chronology(g, cfg=None):
    for fold, tr, vy in folds(cfg):
        g.check(max(tr) < vy, f"fold {fold}: a training year is not before {vy}")


def check_fold_coverage(g, fold_df, cfg=None):
    expected = {vy for _, _, vy in folds(cfg)}
    for name, grp in fold_df.groupby("config"):
        g.check(set(grp.validate_year) == expected,
                f"{name}: folds {sorted(set(grp.validate_year))} != "
                f"{sorted(expected)}")


def check_predictions_complete(g, oof, population, key="draft_year"):
    """Every eligible row must have received a prediction — no complete-case
    deletion anywhere in the pipeline."""
    for name, grp in oof.groupby("config"):
        for vy, gg in grp.groupby(key):
            expect = int((population.draft_year == vy).sum())
            g.check(len(gg) == expect,
                    f"{name} {vy}: {len(gg)} predictions for {expect} prospects "
                    f"— rows were dropped")


def check_artifacts_untracked(g, rel_dir):
    tracked = subprocess.run(["git", "ls-files", rel_dir],
                             capture_output=True, text=True, cwd=ROOT)
    g.check(not tracked.stdout.strip(),
            f"generated artifacts are tracked by Git: "
            f"{tracked.stdout.split()[:5]}")


# ------------------------------------------------------- project entry point
def main():
    """Run every domain's validator and report a summary. Thin CLI wraps this."""
    import data.build as data_build
    import board.scoring as board_scoring
    import team_need.validation as team_need_validation
    import comparables.validation as comparables_validation

    stages = {
        "data": data_build.validate,
        "board": board_scoring.validate,
        "team_need": team_need_validation.validate,
        "comparables": comparables_validation.validate,
    }
    results = {}
    for name, fn in stages.items():
        print(f"\n{'#' * 78}\n# {name.upper()}\n{'#' * 78}")
        results[name] = fn()

    print(f"\n{'=' * 78}\nVALIDATION SUMMARY\n{'=' * 78}")
    for name, code in results.items():
        print(f"  {name:<10} {'PASS' if code == 0 else 'FAIL'}")
    failed = [n for n, c in results.items() if c]
    print(f"\n  {len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0
