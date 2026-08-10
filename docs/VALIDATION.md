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

## 2026 final holdout replay

The one-time, final evaluation of the frozen methodology (FINAL-1). Full
orchestration in `src/replay.py`; run with `scripts/build.py replay-2026`
(Part A) then `scripts/build.py replay-2026-eval` (Part B).

**Pre-holdout freeze.** Commit `bed3c43` ("refactor: simplify DraftLens for
hackathon delivery") was tagged `analytics-freeze-pre-2026` before any 2026
outcome was opened. At that commit, all frozen anchors reproduced exactly:
development population 887/431/456; Draft Probability macro ROC-AUC 0.6986,
pooled 0.6953, Brier 0.2238; Draft Order macro Spearman 0.2968, NDCG 0.9043;
General Board binary AUC 0.7123, graded NDCG 0.8283, drafted-only Spearman
0.2781; Team Need and NBA Comparables validators both passing.

**Prediction artifact.** `data/processed/2026/draftlens_2026_predictions.parquet`,
26 rows, one per 2026 NCAA final early entrant, asserted target-free before
being written. SHA-256 **`67c83fed11bbc4fc0ec012e1d0876b0b394c3d2e945631cab29ca5e5db680b27`**,
recorded in `data/processed/2026/replay_provenance.json` alongside the git
commit, config hashes, model specifications, and draft-size provenance. This
hash was unchanged immediately after the 2026 targets were loaded, and
unchanged again after every evaluation metric below was computed — verified
by `tests/integration/test_replay.py::TestHashImmutability`.

**2026 population/support.** 26 prospects, target-free by construction
(`data.population.load_population` reads only pre-draft identity). After
unsealing: 25 drafted, 1 undrafted (96.2%) — a much more lopsided class than
any historical fold, including 2025's already-flagged 2-undrafted fold.
Actual pick range among drafted: 1–52.

**A note on process integrity.** While sourcing a target-independent 2026
draft size, the operator ran `cat data/raw/draft_population/population_report.csv`
— a diagnostic report written by the acquisition script, outside the modeling
pipeline — and incidentally saw an aggregate row for 2026 (`total_picks=60`,
`drafted=54`, `undrafted=1`) before Part A's freeze. That "54/1" figure
describes the full reconstructed NCAA-drafted population (all early entrants
and non-early-entrants combined); it is not the 26-prospect population this
replay scores, and turned out not to match it (this replay's population
resolves to 25/1, not 54/1). No code path used the figure, and no model,
feature, formula or config was chosen with it in view — but disclosing it is
part of the audit trail this phase requires. The `total_picks=60` figure
alone — a structural, non-outcome fact about the draft as a whole, the same
category already used for 2011–2025 — was used as the 2026 General Board
draft size (`config/board.json`). Separately, this surfaced a real firewall
imprecision: `population_report.csv` mixes population-reconstruction stats
with outcome counts in one file under `draft_population/`, which
`docs/DATA.md`'s firewall principle says should hold pre-draft identity only.
No modeling code reads this file, so it is not a leakage channel, but it is
a documented defect for a future acquisition-script cleanup, not corrected
here to keep this phase's scope to generating and evaluating predictions.

**Draft Probability holdout evaluation.** ROC-AUC 0.9600, average precision
0.9985, Brier 0.1334, log loss 0.4446. Mean probability among drafted 0.675,
among undrafted 0.354 (n=1). **LOW-SUPPORT / DESCRIPTIVE ONLY** — 1 undrafted
prospect cannot support a reliable AUC estimate, and this number is not
compared against the historical 0.6986 as if the two were equally reliable;
it is reported for completeness, not as evidence the model improved.

**Draft Order holdout evaluation** (25 drafted prospects). Spearman 0.1569,
Kendall 0.1133, NDCG 0.9474, NDCG@14 0.8432. Diagnostic only: MAE 11.91 picks,
RMSE 14.32 picks — in the same range as the historical 13.21/15.56 MAE/RMSE,
which does not change the frozen conclusion that the numeric predicted pick
is not product-safe.

**General Board holdout evaluation.** Graded NDCG 0.9462, graded NDCG@14
0.8655, drafted-only Spearman 0.3269, drafted-only Kendall 0.2000, binary AUC
0.9600 (**LOW-SUPPORT / DESCRIPTIVE ONLY**, same 1-undrafted caveat as Draft
Probability). Of the 13 actual top-14 picks, DraftLens's top 14 by rank
contained 8 (61.5% overlap).

**Overall Score audit.** Exactly monotonic with the board signal (asserted by
`tests/integration/test_replay.py`). Distribution: min 2, median 50.0, max 98,
26 unique integer scores for 26 prospects.

**Team Need structural validation.** All 26 prospects scored on all 6
profiles; mean data coverage 99.2%. Eligibility varied by profile as
expected from position mix (Rim Protector and Stretch Big eligible for 13 of
26 — bigs only; the other four profiles eligible for 24–26). No outcome
comparison was made or is reported — Team Need has no ground truth and none
was manufactured for this replay.

**NBA Comparables structural validation.** All 26 prospects returned exactly
3 unique NBA players (0 unavailable, 0 duplicate-player failures, 0
self-match failures). No comparison to later NBA outcomes was made — there
are none to make; these are current-day NBA players, and no NBA career
success was inspected.

**Largest ranking misses** (DraftLens ranked materially lower than the actual
Draft, among drafted prospects): Kingston Flemings (rank 23 → actual pick 8,
gap 15), Keaton Wagler (rank 19 → actual pick 5, gap 14), Morez Johnson Jr.
(rank 22 → actual pick 9, gap 13).

**Largest positive surprises** (DraftLens ranked materially higher than the
actual Draft): Allen Graves (rank 1 → actual pick 19, gap 16), Cameron Carr
(rank 6 → actual pick 24, gap 14), Henri Veesaar (rank 11 → actual pick 52,
gap 14).

**Limitations, specific to this replay.** The 96.2% drafted share makes every
binary metric close to uninformative by construction — a class this lopsided
provides little discrimination signal regardless of model quality, and the
ranking metrics (NDCG, Spearman among drafted) are the only evaluation that
means much here. n=1 undrafted prospect is not enough to say anything about
calibration at the low end.

**No retuning.** Zero analytical changes were made after 2026 outcomes were
loaded. The only code change made during this phase — removing the `2026 not
in years` guard in `comparables.reference.build_ncaa_reference` and adding a
structural `2026: 60` entry to `config/board.json`'s `draft_size_by_year` —
was made and tested *before* Part A ran, is a guard/infrastructure change
rather than a formula or model change, and was verified not to move any
historical anchor. Draft Probability, Draft Order, the General Board formula,
Overall Score, Team Need's dimensions and profiles, and NBA Comparables'
common space and similarity method are byte-for-byte what they were at
`analytics-freeze-pre-2026`.
