"""The single definition of what may never become a DraftLens feature.

Two related but DIFFERENT policies live here, and conflating them would weaken
both:

  FEATURE-FILE POLICY  (`DENY_EXACT`, `DENY_SUBSTRING`, `SUSPICIOUS`)
      Columns that must never be WRITTEN into a feature file at all. Enforced
      when the ML-0 prospect dataset is built.

  MODEL-INPUT POLICY  (`DENIED`, `DENIED_SUBSTR`)
      Columns that may exist in a feature file as identity/audit metadata but
      must never enter X. Broader than the file policy: it also excludes
      identity keys, the target fields, and audit columns that are legitimately
      stored but outcome-correlated.

Why these lists are not merely "post-draft columns": several entries leak
because their AVAILABILITY or GRANULARITY is decided by the outcome, not their
values. Date of birth is 100% present for drafted and 69% for undrafted
prospects; `position_from_population` resolves to a five-position label for 100%
of drafted versus 7.7% of undrafted. A missingness indicator for either would be
the most target-predictive column in the dataset while carrying no basketball
information (ML_SPEC 10.3).

Changing either list changes what the models are allowed to see and requires an
explicit decision in docs/DECISIONS.md.
"""

# --------------------------------------------------------- feature-file policy
DENY_EXACT = {
    "drafted", "pick", "round", "drafting_team", "early_entrant",
    "population_source", "date_of_birth", "age", "current_age", "dob",
    "dob_missing", "draft_year_pick", "nba_player_id", "nba_athlete_id",
    "mock_rank", "consensus_rank", "analyst_rank", "green_room",
    "draft_selection", "draft_round",
    # --- added by the ML-1 audit (DEC-065): dual-source metadata whose
    # granularity/availability is decided by the outcome itself. Drafted
    # players inherit these from the DRAFT RESULTS table, undrafted ones from
    # the early-entrant list, so the label format encodes the target.
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
    # outcome-correlated metadata (DEC-065)
    "early_entrant", "population_source", "position_from_population",
    "class_from_population", "match_method", "match_confidence",
    # age / DOB — availability is a function of the outcome (ML_SPEC 8.2)
    "date_of_birth", "age", "current_age", "dob",
    # identity keys
    "canonical_prospect_id", "player_name", "normalized_name", "college",
    "wikipedia_title", "hoopr_athlete_id", "draft_year",
    # audit-only columns
    "shot_fga_coverage_ratio", "n_teams", "experience_years",
}

# `jump_shot` is excluded because the hoopR shot subcategories are not
# comparable across the 2020/21 schema break (DEC-068).
DENIED_SUBSTR = ("jump_shot", "nba_", "mock", "consensus", "analyst")


def denied_columns(columns):
    """Columns from `columns` that must never enter X. Exact names are matched
    exactly; only DENIED_SUBSTR is matched as a substring — substring-matching
    DENIED would flag legitimate features such as `usage_pct` (it contains
    "age")."""
    return [c for c in columns
            if c in DENIED or any(s in str(c).lower() for s in DENIED_SUBSTR)]


def assert_features_safe(columns, where=""):
    bad = denied_columns(columns)
    if bad:
        raise AssertionError(f"denied features{' in ' + where if where else ''}: {bad}")
    return list(columns)
