"""Distance in the common space, and the exactly-three selection.

Nothing here is learned. There is no ground-truth "correct comparable" dataset,
so there is nothing to fit, and fitting against draft outcomes or NBA career
success would answer a different question entirely.

FOUR RULES, each guarding a specific way this could go wrong:

  COVERAGE-NORMALISED DISTANCE. Distance is computed over dimensions available
  for BOTH players and divided by how many that was. Otherwise a prospect
  missing three dimensions would appear mechanically closer to everyone,
  and the least-measured prospects would get the most confident comparables.

  MINIMUM SHARED COVERAGE. Below it, comparables are UNAVAILABLE. Three names
  produced from two dimensions are not a comparison.

  EXACTLY THREE UNIQUE PLAYERS. The pool holds one row per player, so
  uniqueness is structural rather than a post-hoc de-duplication.

  SELF-MATCH EXCLUSION. A historical prospect who later reached the NBA must
  not return himself. Identity is matched deterministically on normalised name;
  no NBA outcome enters the vector.

The similarity score is an EMPIRICAL DISTANCE PERCENTILE, not a rescaled
distance. `100 - 10 * distance` would be an arbitrary constant pretending to be
a scale.
"""

import numpy as np
import pandas as pd

from comparables.space import DIMENSION_NAMES
from data.matching import normalize_name

N_COMPARABLES = 3

# At least this fraction of dimensions must be present for BOTH players.
MIN_SHARED_COVERAGE = 0.75

UNAVAILABLE = "UNAVAILABLE"
METRICS = ("EUCLIDEAN", "COSINE", "MANHATTAN")

# ------------------------------------------------------- height plausibility
# Height is a CANDIDATE GATE, never a similarity dimension. The six-dimension
# statistical space is unchanged; height only decides WHICH NBA players are
# eligible to be compared against, before any distance is computed.
#
# Windows are tried in order and the FIRST one yielding >= N_COMPARABLES
# eligible players is used, so the rule is deterministic and needs no tuning.
# Chosen from a coverage audit over every scoreable 2026 and 2027 prospect
# (docs/METHODOLOGY.md): +/-2in already gives all 75 prospects at least three
# candidates (median pool 249 of 542), while +/-1in leaves the tallest
# prospect with a single candidate. The wider steps exist so an extreme
# height in a future class degrades gracefully instead of failing.
#
# No window was selected by looking at which NBA names it produced.
HEIGHT_WINDOWS_INCHES = (2, 3, 4)


def _matrix(df, dimensions):
    return df[list(dimensions)].to_numpy(dtype="float64")


def pairwise_distances(prospect_vec, pool_matrix, metric="EUCLIDEAN"):
    """Coverage-normalised distance from one prospect to every pool player.

    Returns (distance, shared_count). Distance is NaN where nothing is shared.
    Every metric is divided by the number of shared dimensions, so a comparison
    over 6 dimensions and one over 4 are on the same scale.
    """
    p = np.asarray(prospect_vec, dtype="float64")
    M = np.asarray(pool_matrix, dtype="float64")
    shared = np.isfinite(p)[None, :] & np.isfinite(M)
    n = shared.sum(axis=1)

    diff = np.where(shared, M - p[None, :], 0.0)
    with np.errstate(invalid="ignore", divide="ignore"):
        if metric == "EUCLIDEAN":
            d = np.sqrt((diff ** 2).sum(axis=1) / np.where(n > 0, n, np.nan))
        elif metric == "MANHATTAN":
            d = np.abs(diff).sum(axis=1) / np.where(n > 0, n, np.nan)
        elif metric == "COSINE":
            # Percentile vectors are all-positive, so raw cosine would call
            # every pair similar. Centre on the 50th percentile first, which
            # turns each axis into "above or below a typical peer" and makes
            # the angle meaningful.
            pc = np.where(shared, p[None, :] - 50.0, 0.0)
            mc = np.where(shared, M - 50.0, 0.0)
            num = (pc * mc).sum(axis=1)
            den = np.sqrt((pc ** 2).sum(axis=1)) * np.sqrt((mc ** 2).sum(axis=1))
            d = 1.0 - np.where(den > 0, num / np.where(den > 0, den, np.nan),
                               np.nan)
        else:
            raise ValueError(metric)
    d = np.where(n > 0, d, np.nan)
    return d, n


def within_pool_percentile(distances):
    """Share of THIS prospect's pool that is farther away, 0-100.

    MEASURED AND REJECTED as the product score. It is structurally degenerate
    for the top three: with a pool of 542, the three closest players are always
    the top 0.55%, so this returns 100.00 / 99.82 / 99.63 for EVERY prospect —
    identical numbers whether the nearest match is excellent (distance 8.9) or
    poor (15.6). Retained because the ML-8 report compares the two transforms.
    """
    d = np.asarray(distances, dtype="float64")
    ok = np.isfinite(d)
    out = np.full(len(d), np.nan)
    if ok.sum() == 0:
        return out
    valid = d[ok]
    n = valid.size
    order = np.argsort(valid, kind="stable")
    ranks = np.empty(n, dtype="float64")
    ranks[order] = np.arange(n, dtype="float64")
    out[ok] = 100.0 * (n - 1 - ranks) / max(1, n - 1)
    return np.clip(out, 0.0, 100.0)


def similarity_scores(distances, reference_distances):
    """EMPIRICAL DISTANCE PERCENTILE against a FROZEN global reference, 0-100.

    A score of 95 means: this prospect-to-NBA-player pairing is closer than
    roughly 95% of all prospect-to-NBA pairings in the frozen development
    reference distribution.

    The reference is the distribution of every distance computed across
    development prospects, so the scale is ABSOLUTE — a genuinely close match
    scores higher than a distant one, which the within-pool variant cannot
    express. No arbitrary constant is involved: `100 - 10 * distance` would be
    a made-up scale wearing a percentage sign.

    NOT a probability, and NOT a percentage of shared traits.
    """
    d = np.asarray(distances, dtype="float64")
    ref = np.sort(np.asarray(reference_distances, dtype="float64"))
    ref = ref[np.isfinite(ref)]
    out = np.full(len(d), np.nan)
    ok = np.isfinite(d)
    if ref.size == 0 or ok.sum() == 0:
        return out
    # share of the reference distribution that is FARTHER than this pairing
    lo = np.searchsorted(ref, d[ok], side="left")
    hi = np.searchsorted(ref, d[ok], side="right")
    mid = (lo + hi) / 2.0
    out[ok] = 100.0 * (ref.size - mid) / ref.size
    return np.clip(out, 0.0, 100.0)


def build_distance_reference(prospect_dims, pool_dims, dimensions=None,
                             metric="EUCLIDEAN", max_prospects=None, seed=20260808):
    """The frozen distribution of prospect-to-NBA distances.

    Computed once over development prospects and then held fixed, so the
    similarity scale cannot drift with whoever is being scored.
    """
    dimensions = list(dimensions if dimensions is not None else DIMENSION_NAMES)
    M = _matrix(pool_dims, dimensions)
    rows = prospect_dims
    if max_prospects and len(rows) > max_prospects:
        rows = rows.sample(max_prospects, random_state=seed)
    out = []
    for _, r in rows.iterrows():
        p = np.asarray([r.get(d, np.nan) for d in dimensions], dtype="float64")
        if not np.isfinite(p).any():
            continue
        d, _ = pairwise_distances(p, M, metric)
        out.append(d[np.isfinite(d)])
    return np.concatenate(out) if out else np.array([])


def _self_match_mask(pool, prospect_name):
    """Deterministic identity exclusion for historical audits.

    A prospect who later became an NBA player must not be his own comparable.
    Matched on the canonical normalised name — no draft or career field is read.
    """
    if not prospect_name:
        return np.zeros(len(pool), dtype=bool)
    key = normalize_name(prospect_name)
    return pool["_name_key"].to_numpy() == key


def height_gate(prospect_height, pool_heights, n=N_COMPARABLES,
                windows=HEIGHT_WINDOWS_INCHES, base_mask=None):
    """Which NBA players are physically plausible comparables, and at what
    window. Applied BEFORE any distance is computed.

    Returns (mask, window_used). `window_used` is None when no window yields
    `n` candidates, or when height is unavailable — in which case the mask is
    all-False and the caller must report the comparison UNAVAILABLE rather
    than fall back to an ungated pool. A missing height NEVER bypasses the
    gate silently: an unmeasured player is not a plausible-height match, it
    is an unknown one.
    """
    heights = np.asarray(pool_heights, dtype="float64")
    empty = np.zeros(len(heights), dtype=bool)
    base = np.ones(len(heights), dtype=bool) if base_mask is None \
        else np.asarray(base_mask, dtype=bool)

    if prospect_height is None or not np.isfinite(prospect_height):
        return empty, None
    # A pool player with no height cannot be shown to be plausible.
    has_height = np.isfinite(heights)
    for window in windows:
        mask = base & has_height & (np.abs(heights - float(prospect_height)) <= window)
        if int(mask.sum()) >= n:
            return mask, int(window)
    return empty, None


def find_comparables(prospect_row, pool, pool_dims, dimensions=None,
                     metric="EUCLIDEAN", n=N_COMPARABLES,
                     min_coverage=MIN_SHARED_COVERAGE, prospect_name=None,
                     exclude_self=True, distance_reference=None,
                     prospect_height=None, height_windows=HEIGHT_WINDOWS_INCHES,
                     apply_height_gate=True):
    """Exactly `n` unique NBA players, closest first, among physically
    plausible candidates.

    Two stages, in this order:
      1. HEIGHT GATE — restrict the pool to NBA players within an adaptive
         height window of the prospect (see `height_gate`).
      2. STATISTICAL SIMILARITY — the UNCHANGED six-dimension coverage-
         normalised distance, over the gated candidates only.

    Height never enters the distance itself, so two candidates who survive
    the gate are ranked exactly as they were before this gate existed.

    Returns a dict with the comparables and the diagnostics needed to judge
    them: coverage, raw distance, the height window used, and the
    3rd-vs-4th margin that says whether the third name is clearly separated
    or nearly arbitrary.
    """
    dimensions = list(dimensions if dimensions is not None else DIMENSION_NAMES)
    p = np.asarray([prospect_row.get(d, np.nan) for d in dimensions],
                   dtype="float64")
    available = int(np.isfinite(p).sum())
    coverage = available / len(dimensions)

    if coverage < min_coverage:
        return {"status": UNAVAILABLE,
                "reason": f"prospect has {available}/{len(dimensions)} "
                          f"dimensions, below the {min_coverage:.0%} minimum",
                "comparables": [], "prospect_coverage": coverage}

    M = _matrix(pool_dims, dimensions)
    d, shared = pairwise_distances(p, M, metric)

    need = int(np.ceil(min_coverage * len(dimensions)))
    ok = np.isfinite(d) & (shared >= need)
    if exclude_self:
        ok &= ~_self_match_mask(pool, prospect_name)

    height_window_used = None
    if apply_height_gate:
        pool_heights = (pool["height_inches"].to_numpy(dtype="float64")
                        if "height_inches" in pool.columns
                        else np.full(len(pool), np.nan))
        gate_mask, height_window_used = height_gate(
            prospect_height, pool_heights, n=n, windows=height_windows,
            base_mask=ok)
        if height_window_used is None:
            reason = ("prospect height is unavailable, so no physically "
                      "plausible NBA candidate pool can be formed"
                      if prospect_height is None
                      or not np.isfinite(prospect_height)
                      else f"fewer than {n} NBA players fall within "
                           f"±{max(height_windows)}in of the prospect")
            return {"status": UNAVAILABLE, "reason": reason,
                    "comparables": [], "prospect_coverage": round(coverage, 3),
                    "height_window_inches": None,
                    "prospect_height_inches": (
                        int(prospect_height)
                        if prospect_height is not None
                        and np.isfinite(prospect_height) else None)}
        ok = gate_mask

    if ok.sum() < n:
        return {"status": UNAVAILABLE,
                "reason": f"only {int(ok.sum())} eligible NBA players meet the "
                          f"shared-coverage minimum; {n} are required",
                "comparables": [], "prospect_coverage": coverage}

    ref = (distance_reference if distance_reference is not None
           else d[np.isfinite(d)])
    scores = similarity_scores(np.where(ok, d, np.nan), ref)
    idx = np.flatnonzero(ok)
    # deterministic ties: exact distance, then the stable analytical id
    order = sorted(idx, key=lambda i: (float(d[i]), int(pool.athlete_id.iloc[i])))
    top = order[:n]

    margin = None
    if len(order) > n:
        margin = float(d[order[n]] - d[order[n - 1]])

    has_pool_height = "height_inches" in pool.columns
    p_height = (int(prospect_height)
                if prospect_height is not None and np.isfinite(prospect_height)
                else None)

    out = []
    for rank, i in enumerate(top, start=1):
        nba_height = (pool["height_inches"].iloc[i] if has_pool_height
                      else np.nan)
        nba_height = (int(nba_height) if np.isfinite(nba_height) else None)
        out.append({
            "rank": rank,
            "nba_player_id": int(pool.athlete_id.iloc[i]),
            "nba_player_name": str(pool.athlete_display_name.iloc[i]),
            "nba_height_inches": nba_height,
            "height_difference_inches": (abs(nba_height - p_height)
                                         if nba_height is not None
                                         and p_height is not None else None),
            "reference_seasons": list(pool.reference_seasons.iloc[i]),
            "similarity_score": int(round(float(scores[i]))),
            "raw_distance": round(float(d[i]), 4),
            "shared_dimension_count": int(shared[i]),
            "comparison_coverage": round(float(shared[i]) / len(dimensions), 3),
        })
    return {"status": "OK", "comparables": out,
            "prospect_coverage": round(coverage, 3),
            "prospect_height_inches": p_height,
            "height_window_inches": height_window_used,
            "third_vs_fourth_margin": (round(margin, 4)
                                       if margin is not None else None),
            "pool_size": int(ok.sum())}


def prepare_pool(pool, heights=None, require_heights=True):
    """Attach the identity key used for self-match exclusion, and the NBA
    heights the plausibility gate needs.

    Heights are joined on `athlete_id` — the SAME stable id the pool is built
    on and the same one ESPN's athlete endpoint is keyed by — so this is an
    exact identity join with no name matching and therefore no name
    ambiguity. A player ESPN has no height for keeps NaN and is simply never
    an eligible candidate; nothing is imputed.
    """
    out = pool.copy()
    out["_name_key"] = out.athlete_display_name.map(normalize_name)

    # Idempotent: a pool that already carries heights (a caller that joined
    # them itself, or a test fixture) is left alone rather than double-merged.
    if "height_inches" in out.columns:
        out["height_inches"] = pd.to_numeric(out.height_inches, errors="coerce")
        return out

    if heights is None:
        from data.espn_athletes import load_nba_heights
        heights = load_nba_heights()

    if heights is None:
        if require_heights:
            raise FileNotFoundError(
                "NBA heights not acquired — run "
                "`python scripts/acquire.py nba-heights`. The comparables "
                "height gate refuses to run ungated.")
        out["height_inches"] = np.nan
        return out

    h = heights[["athlete_id", "height_inches"]].drop_duplicates("athlete_id")
    assert h.athlete_id.is_unique, "duplicate athlete_id in the NBA height table"
    out = out.merge(h, on="athlete_id", how="left")
    out["height_inches"] = pd.to_numeric(out.height_inches, errors="coerce")
    return out
