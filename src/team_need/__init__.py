"""Team Need — deterministic, preference-based prospect fit scoring.

The second DraftLens product mode, and analytically distinct from the first:

    General Draft Board asks  "who looks strongest overall?"   -> predictive
    Team Need asks            "who best fits what we want?"    -> preference

Team Need is NOT a predictive model. It has no ground-truth target — there is no
historical label saying which prospect "correctly fitted" a team — so nothing
here is or may be fitted. Every weight is a basketball or user preference, and
no formula may be optimised against drafted/undrafted, draft pick, Stage A
probability, the Overall Score, NBA outcomes or mock drafts (DEC-101).

It must be able to rank a lower-Overall prospect above a higher-Overall one when
that prospect better matches the requested traits. That is the entire point of
the mode, which is why the General Board's output never enters a Fit Score.

    dimensions.py     factual dimensions on an NCAA peer-percentile scale
    profiles.py       the six predefined archetypes
    scoring.py        custom weighting, Fit Score, ranking
    explanations.py   deterministic strengths and limiting components
    reference.py      the NCAA peer percentile reference
    validation.py     configuration and score guards

Athleticism is UNAVAILABLE and is not scored: there is no athleticism
measurement in the data, and dunk rate is a style signal confounded by position
and role, not a vertical leap (ML_SPEC 18.2, DEC-103).
"""

from team_need.dimensions import (CONFIG, DIMENSIONS,
                                            compute_dimensions, data_coverage)
from team_need.profiles import (PROFILES, profile_names,
                                          score_all_profiles, score_profile)
from team_need.scoring import (SUPPORTED_DIMENSIONS, UnsupportedNeed,
                                         custom_fit, fit_score, profile_fit,
                                         rank_fit, validate_weights)

__all__ = ["CONFIG", "DIMENSIONS", "PROFILES", "SUPPORTED_DIMENSIONS",
           "UnsupportedNeed", "compute_dimensions", "custom_fit",
           "data_coverage", "fit_score", "profile_fit", "profile_names",
           "rank_fit", "score_all_profiles", "score_profile",
           "validate_weights"]
