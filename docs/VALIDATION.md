# DraftLens — Validation

The evidence behind `docs/METHODOLOGY.md`, and the honest limitations that
came with it. Every number below is asserted byte-identical by
`tests/integration/test_frozen_anchors.py` (tolerance 1e-4) and reproduced
live by `board.scoring.validate()` / `team_need.validation.validate()` /
`comparables.validation.validate()` (`scripts/validate.py`).

## General Board

**Fold design.** Seven expanding-window folds, always trained on years
strictly before the validated year, never touching 2026:

| Fold | Train | Validate |
| --- | --- | --- |
| 1 | 2014–2018 | 2019 |
| 2 | 2014–2019 | 2020 |
| 3 | 2014–2020 | 2021 |
| 4 | 2014–2021 | 2022 |
| 5 | 2014–2022 | 2023 |
| 6 | 2014–2023 | 2024 |
| 7 | 2014–2024 | 2025 |

**Draft Probability** (§2.1): macro ROC-AUC **0.6986**, pooled ROC-AUC
**0.6953**, macro Brier **0.2238**, expected calibration error **0.0590**. A
real but limited signal — a transparent within-position percentile baseline
alone reaches 0.6943, so the model's edge over an interpretable heuristic is
modest.

**Draft Order** (§2.2): macro Spearman **0.2968**, macro Kendall **0.2089**,
macro NDCG **0.9043**, macro NDCG@14 **0.7555**, MAE **13.21 picks**, RMSE
**15.56 picks**. Spearman is positive in every one of the 7 folds — the model
never ranks a draft class backwards, but the correlation itself is modest.

**General Board**: binary macro ROC-AUC **0.7123**, average precision
**0.7237**, graded NDCG **0.8283**, drafted-only Spearman **0.2781**,
drafted-only Kendall **0.1973**.

**Draft Order's incremental value is real but modest.** A Draft-Probability-only
reference board (ignoring Draft Order entirely) reaches AUC 0.6986, graded
NDCG 0.8159, drafted Spearman 0.2461 — the combined board beats it on every
one of those headline metrics, which is the entire justification for
including Draft Order in the board at all, but the margin is not large.

**2025 low-negative-support caveat.** The 2025 validation fold has only 2
undrafted prospects. Its **binary** classification metrics (ROC-AUC, average
precision) are flagged `low_negative_support` and must not drive any
methodology decision — two negative examples cannot support a stable AUC
estimate. 2025's **ranking** metrics (Draft Order, graded NDCG) are unaffected
by this and remain sound, since they don't depend on the drafted/undrafted
split.

## Leakage findings

- **Population leakage** — an earlier population rule (union of drafted
  players and notable undrafted players) let post-draft notability decide who
  was even in the sample: 212 of 212 non-early-entrants were drafted,
  100%. Closed by restricting the population to final NCAA early entrants
  only (`docs/DATA.md` §3).
- **Position leakage** — `position_from_population` and
  `class_from_population` are dual-sourced by outcome: drafted prospects
  inherit a fine five-position label from the draft results table, undrafted
  prospects inherit a broad label from the early-entrant list. Measured: 100%
  resolution for drafted vs. 7.7% for undrafted. Closed by using only the
  coarse, near-uniformly-available `hoopr_position` (`docs/DATA.md` §7).
- **DOB/missingness leakage** — date of birth is 100% present for drafted
  prospects and 69% for undrafted; a missingness indicator would have been
  close to the single most target-predictive column in the dataset while
  carrying no basketball information. DOB is excluded from modelling entirely.
- **Rejected features** — generic `jump_shot_*` fields (schema break at
  2020/21), any NBA statistic in a pre-draft feature, any external analyst
  ranking as a feature (benchmark-only).
- **Schema hazards** — `athlete_id` dtype mismatch across hoopR files
  (int64 vs. float64) caused a silent 0% join before a shared int-casting
  helper was introduced; shot coordinates carry ±2.1×10⁸ sentinel
  contamination and are never used.

## Team Need

- **No ground truth exists** — there is no ranking Team Need could be
  "correct" against, so nothing here is optimized. Weights, geometric-mean
  combinations, and profile definitions were fixed by basketball logic before
  any historical face-validity check, never adjusted afterward.
- **No draft-target optimization** — verified by static analysis of the
  scoring path (no draft outcome, pick, or NBA field is importable from
  `team_need`'s scoring modules) and by test.
- **Temporal and position stability** — dimension definitions were checked
  for consistency across draft years and across position groups; percentile
  references are season-specific by construction (§3.1 in
  `docs/METHODOLOGY.md`), so a prospect's Fit Score reflects their season's
  peer group, not a global pool that drifts as the game changes.
- **Sensitivity** — arithmetic-mean vs. geometric-mean combination was
  compared directly; geometric mean was kept for conjunctive profiles
  specifically because it does not let one strong pillar mask a near-total
  absence on another, which arithmetic mean does.
- **Distinction from the General Board** — measured historical rank
  correlation between Team Need profile rankings and the General Board:
  ρ = 0.18–0.62 depending on profile. Team Need is not a re-weighting of the
  board; each archetype surfaces materially different players.

## NBA Comparables

- **No ground truth exists** — comparables describe statistical resemblance,
  not career outcomes; nothing is optimized against NBA career success
  (awards, advanced-metric career value), and the comparables package never
  imports a scoring system (verified by test — see
  `docs/METHODOLOGY.md` §4).
- **Exact common metrics** — 12 metrics across 6 dimensions, every one league-
  relative-percentile before comparison (`docs/METHODOLOGY.md` §4.1); ten
  candidate NCAA-side metric families were evaluated and rejected because the
  NBA long-format schema cannot safely reconstruct the team/opponent totals
  they need, or because no NBA shot-location equivalent exists.
- **Stability findings, reported honestly:**
  - Representation choice matters a lot: the latest-season-only
    representation retains only 42% of the same names as the selected
    recent-multi-season representation; the full-career representation
    retains 75% but blurs distinct role eras for long careers, so it stays
    diagnostic-only.
  - Distance metric choice matters less: Manhattan agrees with the selected
    Euclidean distance on 77% of neighbors, Cosine on 74% (and Cosine is
    mathematically undefined for an exactly-average profile — a real
    property, not a hypothetical one).
  - Leave-one-dimension-out stability sits at 45–56%: removing any single
    dimension changes roughly half the returned names. This is evidence *for*
    the methodology (no one dimension dominates the outcome) and evidence
    *against* over-reading any individual result.
- **Leave-one-dimension-out behavior** — the narrow 45–56% *range* across
  dimensions (rather than one dimension driving nearly all of it) is what
  supports keeping all six; if removing one dimension left the result nearly
  unchanged while removing another scrambled it completely, that would be
  reason to reconsider the space.
- **Neighborhood, not ground truth** — the median gap between the 3rd and 4th
  closest NBA player is only ~4% of the raw distance. The output should be
  read as a plausible statistical neighborhood, not three uniquely correct
  names; the report and the product surface both say so.

## Limitations

- Pre-draft NCAA box-score data explains a real but limited share of draft
  outcomes. Workouts, medicals, interviews, and team fit are not in this data
  and never will be — no future phase of DraftLens will fabricate them.
- Draft Order's numeric predicted pick is not accurate enough to display
  (MAE 13.3 of 60 picks); only its ordering is used.
- Team Need's Athleticism dimension is permanently unavailable, not merely
  unimplemented — no source in this project provides it.
- NBA Comparables' third name is frequently one of several near-equally-close
  candidates; treat the list as a neighborhood.
- The 2025 fold's binary board metrics are unstable by construction (2
  undrafted prospects) and are excluded from driving any decision, though
  they remain in the published per-fold record for transparency.
