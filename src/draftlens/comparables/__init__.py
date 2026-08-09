"""NBA statistical comparables — descriptive similarity, never prediction.

For an NCAA prospect, return EXACTLY THREE NBA players whose statistical and
role profiles most resemble his.

    "Based on his relative statistical profile, this prospect most closely
     resembles these NBA player profiles."

NOT: "he will become this player." This is descriptive context, not a career
projection, a ceiling, a floor or a draft outcome. The words "projected",
"expected career", "ceiling", "floor" and "will become" are prohibited
throughout (DEC-110).

Raw production is never compared across leagues — 19 NCAA points per game and
19 NBA points per game are not the same event. Both sides are converted to
percentiles WITHIN THEIR OWN LEAGUE, and the profile shapes are compared.

    nba_features.py   NBA long-format source -> common-semantics metrics
    reference.py      one representation per unique NBA player
    space.py          the shared six-dimension NCAA/NBA space
    similarity.py     distance, exactly-three selection, similarity score
    explanations.py   deterministic per-dimension decomposition
    validation.py     input and output guards

Nothing here is fitted. There is no ground-truth "correct comparable", so no
draft outcome, board signal, Team Need score or NBA career result may influence
the methodology.
"""

from draftlens.comparables.explanations import explain_comparables, explain_pair
from draftlens.comparables.reference import (MIN_GAMES, MIN_MINUTES,
                                             REFERENCE_SEASONS, build_pool,
                                             load_pool)
from draftlens.comparables.similarity import (MIN_SHARED_COVERAGE,
                                              N_COMPARABLES, find_comparables,
                                              prepare_pool, similarity_scores)
from draftlens.comparables.space import (COMMON_METRICS, DIMENSION_NAMES,
                                         DIMENSIONS, build_nba_space,
                                         build_ncaa_space, to_dimensions)

__all__ = ["COMMON_METRICS", "DIMENSIONS", "DIMENSION_NAMES", "MIN_GAMES",
           "MIN_MINUTES", "MIN_SHARED_COVERAGE", "N_COMPARABLES",
           "REFERENCE_SEASONS", "build_nba_space", "build_ncaa_space",
           "build_pool", "explain_comparables", "explain_pair",
           "find_comparables", "load_pool", "prepare_pool",
           "similarity_scores", "to_dimensions"]
