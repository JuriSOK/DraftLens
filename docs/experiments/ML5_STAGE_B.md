# ML-5 — Stage B target and draft-ranking experiments

**Phase:** ML-5 · Stage B target design and model selection
**Scope:** drafted NCAA early entrants, development window **2014–2025 only**
**Status:** complete — Stage B methodology frozen
**Reproduce:** `./.venv/bin/python scripts/experiments/ml5_stage_b_selection.py` then `./.venv/bin/python scripts/experiments/validate_ml5_stage_b.py`

> **2026 holdout firewall.** No 2026 target file was loaded. No Stage B prediction,
> ranking, expected pick or tier was produced for 2026, and no 2026 pick position was
> inspected. Enforced by [`scripts/experiments/validate_ml5_stage_b.py`](../../scripts/experiments/validate_ml5_stage_b.py)
> check 4 and by `tests/test_ml5_stage_b.py::TestHoldoutFirewall`.
>
> **Stage A remained frozen.** ML-5 inherits the DEC-080…085 representation unchanged and
> did not refit, retune or re-evaluate any Stage A decision.

---

---

> ## ⚠ CORRECTION NOTICE — feature representation (added in the R-1 refactor)
>
> This report states in §18 that Stage B inherited Stage A's **`SEASON_RELATIVE`**
> representation. **It did not.** The ML-5 experiment script imported
> `season_relative` but never called it, so every number published in this report
> was measured on the **`STANDARD`** (raw) representation.
>
> **No published number is wrong.** Every metric here — macro Spearman 0.2968,
> pooled 0.3252, Kendall 0.2089, NDCG 0.9043, NDCG@14 0.7555, MAE 13.21,
> RMSE 15.56 — is exactly reproducible and was correctly measured. Only the
> *description* of the representation was wrong.
>
> **What the frozen methodology therefore is:** `Ridge(alpha=10) | RAW_PICK |
> SET_2_BOX_SHOT_PROFILE | STANDARD | train-fold median | position_3 one-hot`.
> `draftlens.ml.stage_b.STAGE_B` and `config/ml/stage_b.json` record `STANDARD`
> because that is what the evidence supports.
>
> **This was NOT silently repaired.** Running Stage B with `SEASON_RELATIVE`
> moves macro Spearman from 0.2968 to 0.2999 — a change of +0.0031, far inside
> the fold SD of 0.124, but a *scientific* change nonetheless. Adopting it
> requires its own evaluation phase and decision, not a refactor. It is recorded
> as open architectural debt.
>
> Consequently §9's claim that the reduced-feature-set variant was the only
> representation sensitivity tested still holds, and the §18 table row
> "Representation | SEASON_RELATIVE" should be read as **STANDARD**.

---

## 1. Executive summary

Stage B asks: among drafted NCAA early entrants, how highly does the pre-draft statistical
profile suggest a prospect should be selected? The product needs a **ranking**, not a pick
prediction, so rank quality drove selection.

**Selected:** `Ridge(alpha=10) | RAW_PICK | SET_2_BOX_SHOT_PROFILE | SEASON_RELATIVE | train-median impute | position_3 one-hot`.

Four findings, and the fourth is the one that matters most for the product.

1. **The target design barely matters — and for a linear model, three of the four
   candidates are provably the same target.** `RAW_PICK`, `PICK_PERCENTILE` and
   `DRAFT_VALUE` are affine images of one another within a draft year, so they cannot
   reorder a linear model's predictions. Measured rank correlation between their induced
   rankings: **0.998**. The residual 0.002 is entirely draft size varying 58–60 across
   years. Averaged over all 12 models the four targets span macro Spearman **0.2596–0.2624**
   — a range of 0.003 against a fold SD of 0.13.
2. **Linear beats nonlinear again.** Every ridge configuration outranks every random
   forest, HistGradientBoosting and gradient-boosting configuration on rank quality
   (ridge 0.282–0.307 macro Spearman vs best nonlinear 0.275). ML-4's lesson repeats
   without needing the low-support argument.
3. **Rank signal is real but modest.** The selected model reaches macro Spearman
   **0.2968** and macro NDCG **0.9043**, against a ranking baseline (B4-style percentile
   composite) of 0.2320, and a position-only baseline that is **negative** (−0.1235).
   Pre-draft NCAA box-score and shot-profile data orders drafted prospects better than
   chance and better than any baseline, but far from strongly.
4. **Exact-pick prediction is NOT product-safe, and the evidence is unambiguous.**
   MAE is **13.2 picks** on a 60-pick draft. Only **21%** of predictions land within 5
   picks. The model regresses hard to the middle: actual lottery picks (mean pick 7.8)
   are predicted at **23.0** on average, and actual second-rounders (mean 44.1) at
   **28.8**. It even emits picks outside the legal range (predicted minimum **−5.1**).
   A "Predicted Pick: 17.3" display would be false precision of the exact kind
   PRODUCT.md §20 and ML_SPEC §17.2 prohibit.

Consequence for the product: Stage B ships as an **ordering signal**, not a pick number.
The three-tier representation is retained alongside it for display, because it is honest
about the resolution the data actually supports.

---

## 2. Stage B population

**431 drafted NCAA early entrants, 2014–2025.** Exactly the `drafted == 1` subset of the
887-prospect Stage A development population — a strict subset, produced by *removing*
undrafted rows, never by relabelling them.

| Draft year | n | min pick | max pick | draft size |
| --- | --: | --: | --: | --: |
| 2014 | 28 | 1 | 55 | 60 |
| 2015 | 27 | 1 | 51 | 60 |
| 2016 | 27 | 2 | 56 | 60 |
| 2017 | 37 | 1 | 55 | 60 |
| 2018 | 39 | 1 | 60 | 60 |
| 2019 | 40 | 1 | 59 | 60 |
| 2020 | 40 | 1 | 59 | 60 |
| 2021 | 50 | 1 | 59 | 60 |
| 2022 | 43 | 1 | 57 | 58 |
| 2023 | 41 | 2 | 58 | 58 |
| 2024 | 33 | 3 | 55 | 58 |
| 2025 | 26 | 1 | 49 | 59 |
| **Total** | **431** | | | |

**No synthetic pick exists anywhere.** No undrafted prospect was assigned 61, 100, 999 or
any sentinel. Validator check 2 fails on any of those values, and a test asserts each one
independently. The population is guarded structurally: a row without a real pick cannot
reach Stage B because it is not drafted.

**All 8 unresolved prospects (no hoopR match) are undrafted**, so Stage B contains **zero**
unresolved prospects. This is a consequence of the Stage A population, not a change to it —
DEC-071 already recorded that every unresolved prospect went undrafted. The Stage A
population is untouched.

Missingness policy carried forward unchanged: train-fold median imputation, no missing
indicators, no complete-case deletion. Every drafted prospect in every validation year
received a prediction from every configuration (validator check 7, 60 configurations).

---

## 3. Temporal folds

The ML-3 expanding-window folds, restricted to drafted prospects. Training is always
strictly earlier than validation.

| Fold | Train | Validate | Train n | Validate n |
| --- | --- | --- | --: | --: |
| 1 | 2014–2018 | 2019 | 158 | 40 |
| 2 | 2014–2019 | 2020 | 198 | 40 |
| 3 | 2014–2020 | 2021 | 238 | 50 |
| 4 | 2014–2021 | 2022 | 288 | 43 |
| 5 | 2014–2022 | 2023 | 331 | 41 |
| 6 | 2014–2023 | 2024 | 372 | 33 |
| 7 | 2014–2024 | 2025 | 405 | 26 |

**Stage B has no degenerate fold.** This is a meaningful difference from Stage A, where the
2025 fold had two undrafted prospects and distorted the entire ML-4 leaderboard (ML4_STAGE_A
§9). Here 2025 validates on 26 drafted prospects — the smallest fold, but a perfectly
well-posed ranking problem. Rank metrics are computable and stable on all seven folds, so
no fold needed to be excluded from selection.

2025 is nevertheless the joint-weakest fold for the selected model (Spearman 0.1556), and
2020 is weaker still (0.1381). Neither is a sample-size artifact: 2020 has 40 prospects.

---

## 4. Historical pick distribution

Across the 431 prospects: mean pick 26.2, median 24, SD 16.2, range 1–60. The distribution
is close to uniform across the draft, which is expected — early entrants populate the whole
board.

**Draft size varies across the window** and this was audited rather than assumed:

| Years | Draft size |
| --- | --- |
| 2014–2021 | 60 |
| 2022–2024 | 58 |
| 2025 | 59 |

Sizes are taken from DATA.md §24.5 (a structural property of each draft, independent of
the ML-0.1 population correction) and are version-controlled in
[`config/ml/stage_b.json`](../../config/ml/stage_b.json).

> **Documentation defect found and corrected.** DATA.md §24.5 records **59** total picks
> for 2014, but pick **60** is present in the raw target file (Cory Jefferson, San Antonio
> Spurs). The documented value is wrong; **60** is used. This was caught by a validator
> check asserting that no observed pick may exceed its declared draft size — a check that
> exists precisely because the `PICK_PERCENTILE` target divides by that number. Every other
> year is consistent. DATA.md is corrected in this commit.

This is also the practical argument against year-normalised targets: they introduce a
dependency on an externally maintained constant that must be correct for every future
class, and the very first year checked was wrong.

### Tier boundaries — density before tradition

ML_SPEC §6.3 requires tier boundaries to be justified against observed density rather than
adopted because they feel natural. The traditional four-tier scheme was inspected first
and **rejected**:

| Scheme | Cells below 5 members | Detail |
| --- | --- | --- |
| Traditional 1–14 / 15–30 / 31–45 / 46–60 | **8 of 48** | Late second: 1 (2025), 2 (2014), 2 (2015), 3 (2016, 2017, 2024) |
| **Adopted 1–14 / 15–30 / 31–60** | **1 of 36** | Only 2025 round 2 = 4 |

Totals for the adopted scheme: 130 lottery / 133 rest-of-first-round / 168 second round.
The 1–14 and 15–30 boundaries are retained because they are **structural** — lottery size
and first-round size — not merely conventional. The two second-round tiers are merged
because the data cannot support their separation. Boundaries are fixed from development
history and never refitted per fold.

---

## 5. Candidate target designs

All four ML_SPEC §6.3 candidates were addressed.

| # | Candidate | Treatment |
| --- | --- | --- |
| **A** | Exact pick regression | `RAW_PICK`, evaluated on all 12 models |
| **B** | Transformed pick | `LOG_PICK` and `DRAFT_VALUE` (inverse pick position), plus `PICK_PERCENTILE` for the draft-size question |
| **C** | Ordinal draft tier | `TIER_3`, multinomial logistic with order-respecting evaluation |
| **D** | Learning to rank | **Evaluated as an evaluation objective only — see below** |

### Candidate D — why no direct ranker was built

scikit-learn provides **no scientifically clean learning-to-rank estimator** for this
setup: there is no LambdaMART, no RankNet, no pairwise or listwise ranking objective.
Installing a ranking library solely to satisfy this candidate is prohibited by the ML-5
brief and would breach DEC-074.

Ranking is therefore treated as the **evaluation objective**: every continuous target
induces a ranking, and rank quality is the primary selection criterion. This is recorded
as a documented limitation, not a silent omission. `test_no_ranking_library_was_installed`
asserts that no such library was added.

### Design

**Full factorial: 12 models × 4 continuous targets = 48 configurations**, all predeclared
in the config before any fold result was inspected, all evaluated on all 7 folds. A full
factorial was chosen over a two-stage "pick a target, then pick a model" search because
the latter makes the second choice conditional on the first. Plus 3 baselines, 1 tier
model, and 8 reduced-feature-set configurations = **60 configurations**.

No random cross-validation anywhere — it would mix draft years and destroy the temporal
guarantee.

---

## 6. Target transformations

| Target | Formula | Direction | Inverse | Rank-preserving |
| --- | --- | --- | --- | --- |
| `RAW_PICK` | `pick` | lower is better | identity | yes |
| `LOG_PICK` | `ln(pick)` | lower is better | `exp(y)` | yes |
| `PICK_PERCENTILE` | `(pick − 1) / (size − 1)` | lower is better | `y(size−1)+1` | yes |
| `DRAFT_VALUE` | `(size + 1 − pick) / size` | **higher is better** | `size+1−y·size` | yes |

All four are verified strictly monotonic, exactly invertible, and rank-preserving by both
the validator (check 8) and unit tests.

### The finding: affine transforms cannot change a linear model's ranking

`RAW_PICK`, `PICK_PERCENTILE` and `DRAFT_VALUE` are affine functions of one another for a
fixed draft size. A linear model fitted on an affine image of a target produces an affine
image of the same prediction — which induces **exactly the same ordering**. Measured:

| Comparison | Rank correlation of induced rankings |
| --- | --- |
| `RAW_PICK` vs `PICK_PERCENTILE` | **0.997949** |
| `RAW_PICK` vs `DRAFT_VALUE` | **0.998033** |
| `RAW_PICK` vs `LOG_PICK` | 0.938173 |

The shortfall from 1.000 in the first two rows is *entirely* attributable to draft size
varying 58–60 across years, which makes the transform piecewise- rather than globally
affine. **`LOG_PICK` is the only genuinely non-affine transformation tested**, and it is
the only one that materially moves the ranking.

At fixed regularisation (α = 10), per-fold Spearman for `PICK_PERCENTILE` and
`DRAFT_VALUE` is **identical to four decimal places on every one of the seven folds**.

Averaged over all 12 models:

| Target | macro Spearman | macro Kendall | macro NDCG | macro MAE | macro RMSE | SD | worst |
| --- | --- | --- | --- | --- | --- | --- | --- |
| LOG_PICK | 0.2624 | 0.1817 | 0.8948 | 13.93 | 17.31 | 0.1383 | −0.1010 |
| DRAFT_VALUE | 0.2614 | 0.1820 | 0.9032 | 13.32 | 15.79 | 0.1344 | −0.0475 |
| PICK_PERCENTILE | 0.2606 | 0.1815 | 0.9033 | 13.32 | 15.79 | 0.1347 | −0.0475 |
| RAW_PICK | 0.2596 | 0.1808 | 0.9024 | 13.36 | 15.81 | 0.1361 | −0.0557 |

`LOG_PICK` leads on Spearman by 0.003 — a fortieth of the fold SD — while being clearly
worst on NDCG (0.8948), MAE (+0.6 picks), RMSE (+1.5) and worst-year (−0.101).

---

## 7. Baselines

| Baseline | macro Spearman | macro Kendall | macro NDCG | macro MAE | macro RMSE | SD | worst year |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B5A global mean pick | **n/a** | n/a | n/a | 14.02 | 16.40 | n/a | n/a |
| B5B position mean pick | **−0.1235** | −0.0950 | 0.8480 | 14.11 | 16.55 | 0.1149 | −0.2465 |
| B5C percentile composite | 0.2320 | 0.1616 | 0.8992 | 14.40 | 16.69 | 0.1226 | −0.0143 |

**B5A is constant, so its rank metrics are reported as null, not as 1.0.** This is
deliberate: ML-3 hit exactly this bug, where a constant predictor inherited source row
order (drafted-first) and scored a spurious NDCG of 1.000. `stage_b_metrics` detects zero
prediction variance and returns null rank metrics; a test enforces it.

Note B5A's MAE of 14.02 — **the global mean pick is within 0.8 picks of the best model's
MAE**. That is the numeric-error result in a sentence, and §12 returns to it.

**B5B is negative.** Position alone does not merely fail to predict pick — it predicts it
*backwards* (−0.1235 macro, worst year −0.2465). This reproduces ML-3's finding
(ML_SPEC §15: Spearman −0.25 to +0.10) on the Stage B population. Coarse position carries
no usable draft-position signal.

**B5C is the bar to clear**, at 0.2320. The selected model reaches 0.2968, a clear margin
of +0.065 — about half a fold SD, and consistent across folds.

---

## 8. Linear models

| Config | macro Spearman | pooled | Kendall | NDCG | NDCG@14 | MAE | RMSE | SD | worst year |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RIDGE_a1 \| RAW_PICK | **0.3072** | **0.3391** | **0.2143** | **0.9169** | **0.7641** | 13.28 | 15.59 | 0.1295 | 0.1308 |
| RIDGE_a10 \| LOG_PICK | 0.3024 | 0.3073 | 0.2078 | 0.9075 | 0.7608 | 14.07 | 17.64 | 0.1508 | 0.1289 |
| RIDGE_a10 \| DRAFT_VALUE | 0.3017 | 0.3291 | 0.2119 | 0.9055 | 0.7500 | 13.14 | 15.52 | **0.1184** | 0.1381 |
| RIDGE_a10 \| PICK_PERCENTILE | 0.3017 | 0.3294 | 0.2119 | 0.9055 | 0.7500 | **13.14** | **15.52** | **0.1184** | 0.1381 |
| **RIDGE_a10 \| RAW_PICK** | **0.2968** | **0.3252** | **0.2089** | **0.9043** | **0.7555** | **13.21** | **15.56** | **0.1242** | **0.1381** |
| RIDGE_a50 \| RAW_PICK | 0.2968 | 0.2996 | 0.2062 | 0.8982 | 0.7552 | 13.18 | 15.56 | 0.1366 | **0.1477** |
| RIDGE_a200 \| RAW_PICK | 0.2893 | 0.2642 | 0.2075 | 0.8990 | 0.7508 | 13.29 | 15.63 | 0.1545 | 0.0962 |
| ENET_a01_l5 \| RAW_PICK | 0.2646 | 0.2434 | 0.1841 | 0.8954 | 0.7462 | 13.36 | 15.75 | 0.1526 | 0.0474 |
| ENET_a03_l5 \| RAW_PICK | 0.1927 | 0.1193 | 0.1330 | 0.8947 | 0.7397 | 13.72 | 15.99 | 0.1892 | −0.0557 |

**ElasticNet is rejected.** Both configurations rank below every ridge configuration, and
the stronger L1 penalty is the worst linear result in the study (0.1927, worst year
−0.0557). This is the same finding as ML-4 §17: with 25 correlated basketball features,
L1's arbitrary selection within a correlated group is a liability, not a simplification.

### Choosing the ridge penalty

The alpha path separates by less than its own noise. Paired per-fold differences against
α = 10 on `RAW_PICK`:

| Config | mean Δ Spearman | SD of Δ | wins |
| --- | --- | --- | --- |
| RIDGE_a1 | +0.0104 | 0.0428 | 5/7 |
| RIDGE_a50 | +0.0000 | 0.0477 | 5/7 |
| RIDGE_a200 | −0.0075 | 0.0886 | 4/7 |

α = 1 leads on macro Spearman by 0.0104 — **a quarter of that difference's own fold SD**.
That is not a difference in rank quality; it is noise. When criteria 1 and 2 are tied
within noise, the selection descends the priority list, and coefficient stability decides:

| Model | α | sign-consistent | mean coefficient fold SD | max abs coefficient |
| --- | --- | --- | --- | --- |
| RIDGE_a1 | 1 | 20/29 | 0.0747 | 0.809 |
| **RIDGE_a10** | **10** | **22/29** | **0.0388** | **0.307** |
| RIDGE_a50 | 50 | 24/29 | 0.0203 | 0.188 |
| RIDGE_a200 | 200 | 23/29 | 0.0103 | 0.091 |

α = 1 nearly doubles coefficient volatility relative to α = 10 and flips two more signs
across folds. PRODUCT.md §16 requires the board to explain deterministically why one
prospect outranks another; a model whose coefficients move that much between folds cannot
support trustworthy explanations. α = 50 is more stable still but gives up pooled Spearman
(0.2996 vs 0.3252), and DEC-075 requires both aggregations to hold up.

α = 10 is the only configuration that is **never worst on any criterion**: best fold SD of
the grid, second on worst-year, second on coefficient stability, and inside noise of the
best macro Spearman.

---

## 9. Nonlinear models

| Config | macro Spearman | pooled | NDCG | MAE | SD | worst year |
| --- | --- | --- | --- | --- | --- | --- |
| GB_d2_lr005 \| RAW_PICK | 0.2686 | 0.2969 | 0.9138 | 13.15 | 0.1269 | 0.0926 |
| RF_d6_leaf10 \| RAW_PICK | 0.2657 | 0.2544 | 0.9076 | 13.38 | 0.1244 | 0.1050 |
| RF_d4_leaf20 \| RAW_PICK | 0.2543 | 0.2318 | 0.8952 | 13.46 | 0.1459 | 0.0715 |
| HGB_lr005_leaf4 \| RAW_PICK | 0.2444 | 0.2782 | 0.9056 | 13.18 | 0.1274 | 0.0031 |
| RF_dNone_leaf30 \| RAW_PICK | 0.2332 | 0.2054 | 0.8942 | 13.53 | 0.1583 | 0.0331 |
| HGB_lr005_leaf8 \| RAW_PICK | 0.2014 | 0.2238 | 0.9041 | 13.54 | 0.1037 | 0.0708 |

Averaged over all four targets, the family ordering is unambiguous:

| Model | macro Spearman (mean over 4 targets) |
| --- | --- |
| RIDGE_a1 | 0.3066 |
| RIDGE_a10 | 0.3007 |
| RIDGE_a50 | 0.2932 |
| RIDGE_a200 | 0.2817 |
| GB_d2_lr005 | 0.2749 |
| RF_d6_leaf10 | 0.2661 |
| ENET_a01_l5 | 0.2620 |
| HGB_lr005_leaf4 | 0.2504 |
| RF_d4_leaf20 | 0.2502 |
| RF_dNone_leaf30 | 0.2270 |
| HGB_lr005_leaf8 | 0.2157 |
| ENET_a03_l5 | 0.2032 |

**Every ridge configuration outranks every nonlinear configuration.** Unlike ML-4, this
did not require a low-support sensitivity argument to establish — the ordering is direct,
and the best nonlinear model (GB depth 2) sits 0.032 below the selected ridge and 0.038
below the best. Nonlinear models are rejected for Stage B on the same complexity principle
that rejected them for Stage A (ML_SPEC §16).

The one place nonlinear models are competitive is MAE (GB 13.15 vs ridge 13.21) — which
§12 shows is the metric that carries almost no information here.

**Reduced feature set.** `SET_2R_REDUCED` (21 features) was tested on the ridge family as
a declared collinearity check. It changes little and is slightly worse:
`RIDGE_a10|RAW_PICK|SET_2R` scores 0.2910 macro / 0.3193 pooled against 0.2968 / 0.3252 for
the full set, with a worse worst-year (0.1195 vs 0.1381). The full `SET_2_BOX_SHOT_PROFILE`
is retained, consistent with DEC-081.

---

## 10. Ordinal / tier experiment

`TIER3_MULTINOMIAL_LR` — multinomial logistic regression over the three tiers, with ranking
induced from the **expected tier index** (Σ P(tier) × tier).

> **Stated limitation, not glossed over.** scikit-learn provides no native ordinal-regression
> estimator. This is multinomial classification, and **the estimator does not know the tiers
> are ordered** — only the evaluation does. It must not be described as ordinal regression.
> The limitation is recorded in the config and asserted by a test.

| Year | n | Spearman | NDCG | exact tier | adjacent tier | ordered distance | macro F1 |
| --- | --: | --- | --- | --- | --- | --- | --- |
| 2019 | 40 | 0.3818 | 0.9146 | 0.475 | 0.725 | 0.800 | 0.471 |
| 2020 | 40 | 0.0529 | 0.8925 | 0.425 | 0.700 | 0.875 | 0.400 |
| 2021 | 50 | 0.3815 | 0.8841 | 0.480 | 0.860 | 0.660 | 0.408 |
| 2022 | 43 | 0.4126 | 0.9354 | 0.442 | 0.861 | 0.698 | 0.354 |
| 2023 | 41 | 0.2695 | 0.8814 | 0.439 | 0.854 | 0.707 | 0.372 |
| 2024 | 33 | 0.3563 | 0.9360 | 0.333 | 0.818 | 0.849 | 0.320 |
| 2025 | 26 | 0.2704 | 0.9331 | 0.346 | 0.731 | 0.923 | 0.314 |
| **macro** | | **0.3036** | **0.9110** | **0.420** | **0.793** | **0.787** | **0.377** |

The tier model is **genuinely competitive as a ranker** — macro Spearman 0.3036, second
only to `RIDGE_a1` among all 60 configurations, with the second-best NDCG@14 (0.7714). It
is not selected as the ranking model because its worst-year Spearman is materially weaker
(0.0529 vs 0.1381), its pooled Spearman is lower (0.3062 vs 0.3252), and it cannot produce
a pick-scale error at all.

But its **exact tier accuracy of 42%** and **adjacent-tier accuracy of 79%** are the most
interpretable statement of Stage B's real resolution in this entire report: the data
places a prospect in roughly the right third of the draft about four times in five, and
in exactly the right third about twice in five. That is worth displaying, and §19 acts on it.

---

## 11. Fold-by-fold ranking metrics — selected model

`RIDGE_a10 | RAW_PICK`:

| Year | n | n train | Spearman | Kendall τ | NDCG | NDCG@14 | lottery recall@14 | R1 recall@30 |
| --- | --: | --: | --- | --- | --- | --- | --- | --- |
| 2019 | 40 | 158 | 0.3600 | 0.2462 | 0.9024 | 0.7631 | 0.462 | 0.826 |
| 2020 | 40 | 198 | 0.1381 | 0.0846 | 0.9054 | 0.6790 | 0.455 | 0.810 |
| 2021 | 50 | 238 | 0.3432 | 0.2571 | 0.8531 | 0.6768 | 0.545 | 0.800 |
| 2022 | 43 | 288 | 0.4887 | 0.3400 | 0.9381 | 0.8502 | 0.667 | 0.800 |
| 2023 | 41 | 331 | 0.2486 | 0.1537 | 0.8875 | 0.7297 | 0.444 | 0.840 |
| 2024 | 33 | 372 | 0.3432 | 0.2424 | 0.9212 | 0.7833 | 0.625 | 0.947 |
| 2025 | 26 | 405 | 0.1556 | 0.1385 | 0.9227 | 0.8064 | 0.615 | 1.000 |
| **macro** | | | **0.2968** | **0.2089** | **0.9043** | **0.7555** | **0.545** | **0.860** |

Spearman is **positive in all seven folds** — the model never ranks a class backwards. The
spread is wide (0.138–0.489, SD 0.124), which is the honest characterisation: the signal
is real but its strength varies substantially by class.

### Board-level, among in-scope NCAA early entrants

> **These figures cover only NCAA early entrants.** Stage B does not see automatically
> eligible seniors or international prospects, so this is **not** a reproduction of the
> real NBA first round. DraftLens does not predict every real NBA first-rounder and must
> never be described as doing so.

Within that population the model recovers **54.5%** of actual lottery picks in its top 14
and **86.0%** of actual first-rounders in its top 30. The first-round figure is strong;
the lottery figure — barely better than a coin flip on the picks that matter most — is the
weaker and more important number.

---

## 12. Numeric error

| Config | macro MAE | macro RMSE | macro median AE |
| --- | --- | --- | --- |
| RIDGE_a10 \| PICK_PERCENTILE | **13.14** | **15.52** | 13.12 |
| GB_d2_lr005 \| RAW_PICK | 13.15 | 15.75 | 13.02 |
| RIDGE_a50 \| RAW_PICK | 13.18 | 15.56 | 13.15 |
| **RIDGE_a10 \| RAW_PICK** | **13.21** | **15.56** | **13.26** |
| RIDGE_a1 \| RAW_PICK | 13.28 | 15.59 | 12.84 |
| RIDGE_a10 \| LOG_PICK | 14.07 | 17.64 | 12.29 |
| **B5A global mean pick** | **14.02** | **16.40** | — |
| B5C percentile composite | 14.40 | 16.69 | — |

**The entire field spans 13.1–14.4 MAE, and predicting the training-fold mean pick for
everyone scores 14.02.** The best model beats a constant by **0.8 picks**. Selecting on
lowest RMSE — explicitly prohibited by the ML-5 brief — would have been selecting on
approximately nothing.

Note `LOG_PICK` has the *best* median AE (12.29) and the *worst* MAE (14.07) and RMSE
(17.64). That is the log transform behaving exactly as designed: it tightens the middle of
the distribution and pays for it with large errors in the tail, since an error in log space
becomes a multiplicative error in picks. It is a coherent trade, but it buys no rank
quality, so it is not worth taking.

---

## 13. NDCG / board ranking

Relevance is defined as `draft_size + 1 − pick`, so pick 1 carries the highest gain, with
linear gains and the standard log₂ positional discount.

| Config | macro NDCG | NDCG@5 | NDCG@10 | NDCG@14 | worst-year NDCG |
| --- | --- | --- | --- | --- | --- |
| RIDGE_a1 \| RAW_PICK | **0.9169** | — | — | **0.7641** | — |
| GB_d2_lr005 \| RAW_PICK | 0.9138 | — | — | 0.7586 | — |
| TIER3_MULTINOMIAL_LR | 0.9110 | — | — | 0.7714 | — |
| **RIDGE_a10 \| RAW_PICK** | **0.9043** | — | — | **0.7555** | **0.8531** |
| B5C percentile composite | 0.8992 | — | — | 0.7277 | — |
| B5B position mean pick | 0.8480 | — | — | — | — |

**A caution on reading full-list NDCG here.** Every configuration scores 0.85–0.92, and
even the perverse position baseline reaches 0.848. With a population of 26–50 already-drafted
prospects, full-list NDCG is compressed near the top of its range and discriminates poorly.
**NDCG@14 is the more informative variant** (0.73–0.77 across serious candidates) because it
concentrates on the part of the board that matters. Spearman remains the primary criterion
for exactly this reason.

---

## 14. Temporal stability

| Config | macro Spearman | fold SD | worst year | best year |
| --- | --- | --- | --- | --- |
| RIDGE_a10 \| PICK_PERCENTILE | 0.3017 | **0.1184** | 0.1381 | 0.4887 |
| **RIDGE_a10 \| RAW_PICK** | **0.2968** | **0.1242** | **0.1381** | **0.4887** |
| RIDGE_a1 \| RAW_PICK | 0.3072 | 0.1295 | 0.1308 | 0.4923 |
| RIDGE_a50 \| RAW_PICK | 0.2968 | 0.1366 | **0.1477** | 0.5000 |
| RIDGE_a10 \| LOG_PICK | 0.3024 | 0.1508 | 0.1289 | 0.5467 |
| RIDGE_a200 \| RAW_PICK | 0.2893 | 0.1545 | 0.0962 | 0.4544 |
| TIER3_MULTINOMIAL_LR | 0.3036 | 0.1238 | 0.0529 | 0.4126 |
| HGB_lr005_leaf4 \| RAW_PICK | 0.2444 | 0.1274 | 0.0031 | 0.4194 |

Fold SD of 0.124 against a macro of 0.297 means the year-to-year variation is roughly 40%
of the signal. **No Stage B configuration is temporally stable in an absolute sense.** The
selected model is among the steadier options and never turns negative, but a single class
can land anywhere between 0.14 and 0.49.

Weakest years are 2020 (0.138) and 2025 (0.156). 2020 is not a small-sample effect (40
prospects) — it is the pandemic-shortened NCAA season, where the pre-draft statistical
record is genuinely thinner and less comparable. 2021, the COVID eligibility cohort, is
*not* anomalous for Stage B (0.343), unlike its outsized effect on Stage A.

---

## 15. Residual / exact-pick uncertainty

This section determines the product recommendation.

| Statistic | Value |
| --- | --- |
| MAE | **13.28 picks** |
| Median absolute error | 12.86 picks |
| 90th percentile absolute error | **24.75 picks** |
| Within 5 picks | **20.9%** |
| Within 10 picks | 38.1% |
| Within 15 picks | 62.3% |
| Predicted range | **−5.1 to 51.3** |
| Actual range | 1 to 59 |

Error by actual tier — the shrinkage is severe and systematic:

| Actual tier | n | MAE | mean predicted pick | mean actual pick |
| --- | --: | --- | --- | --- |
| Lottery (1–14) | 77 | 15.35 | **23.01** | **7.82** |
| Rest of R1 (15–30) | 83 | 7.60 | 27.14 | 22.60 |
| Round 2 (31–60) | 113 | 16.03 | **28.84** | **44.05** |

Four independent facts, each sufficient on its own:

1. **MAE of 13.3 picks on a 60-pick draft** is more than a full round of error, and only
   0.8 picks better than predicting the mean for everyone.
2. **Only 1 prediction in 5 lands within 5 picks** of the truth.
3. **The model predicts illegal picks.** Its minimum prediction is **−5.1**. A displayed
   "predicted pick" would sometimes be a number that cannot exist.
4. **Predictions collapse toward the middle.** The model compresses a true 1–59 range into
   roughly −5 to 51, and — critically — it predicts actual lottery picks at an average of
   pick 23 and actual second-rounders at an average of pick 29. **The two groups' mean
   predictions differ by less than 6 picks while their actual means differ by 36.** This
   is ordinary regression-to-the-mean under a weak signal, but it means a numeric pick
   display would systematically understate elite prospects and overstate marginal ones.

**Conclusion: exact numeric pick output is not display-safe.** The ranking it induces is
useful; the number itself is not. No formal uncertainty interval was constructed — none is
naturally available from ridge without distributional assumptions the data does not
support — but the residual spread above is more than sufficient to settle the product
question.

---

## 16. Interpretability sanity

Coefficients from the selected model, negated so that **positive means "pushes toward an
earlier pick"**. 22 of 29 terms are sign-consistent across all 7 folds.

| Feature | Full window | Sign-consistent | Fold SD |
| --- | --- | --- | --- |
| `height` | **+0.337** | yes | 0.046 |
| `points_per_40` | **+0.278** | yes | 0.051 |
| `position_3=C` | **−0.262** | yes | 0.048 |
| `position_3=G` | +0.258 | yes | 0.058 |
| `rim_attempt_share` | +0.233 | yes | 0.043 |
| `three_point_attempt_rate` | +0.214 | yes | 0.040 |
| `layup_attempt_share` | −0.200 | yes | 0.063 |
| `unassisted_made_fg_share` | +0.181 | yes | 0.058 |
| `steals_per_40` | +0.139 | yes | 0.014 |
| `ts_pct` | +0.133 | yes | 0.036 |
| `reb_per_40` | −0.128 | **no** | 0.087 |
| `rim_make_pct` | +0.120 | yes | 0.028 |
| `weight` | +0.117 | yes | 0.012 |
| `usage_pct` | −0.116 | **no** | 0.075 |
| `assists_per_40` | −0.027 | yes | 0.021 |

**Basketball reading.** Height is the single strongest driver of draft position — larger
prospects go earlier, which matches how NBA teams actually draft. Scoring rate, rim
pressure, three-point volume, self-creation (`unassisted_made_fg_share`), true shooting
and steals all push toward earlier picks. Being a centre pushes later and being a guard
earlier, after controlling for the rest.

**Two suspicious coefficients, investigated rather than celebrated:**

- **`reb_per_40` is negative (−0.128) and sign-inconsistent** — it is positive in 2019–2020
  and negative from 2021 onward. Rebounding is heavily position-confounded, and with
  `height`, `weight` and `position_3=C` all in the model, the rebounding term is absorbing
  a residual effect rather than measuring rebounding value. It should not be read as
  "rebounding hurts draft stock".
- **`usage_pct` is negative (−0.116) and sign-inconsistent**, and it correlates 0.853 with
  `points_per_40` (measured in ML-4 §6). This is the same collinearity pair ML-4 flagged.
  The two must be read jointly, not individually.

Both are cases where the joint fit is sound but the individual coefficient is not
interpretable. This is the same caveat as ML4_STAGE_A §15 and constrains how explanations
may be generated in ML-6.

---

## 17. 2011–2013 robustness

Applied **only after** the methodology was selected on 2014–2025. The robustness years
never entered target choice, model choice, preprocessing, hyperparameters, or any
out-of-fold selection prediction — enforced by validator check 10.

The selected model, trained on all of 2014–2025, applied to 85 drafted early entrants:

| Year | n | Spearman | Kendall τ | NDCG | MAE | RMSE | lottery recall@14 |
| --- | --: | --- | --- | --- | --- | --- | --- |
| 2011 | 27 | 0.3370 | 0.2422 | 0.9464 | 13.78 | 17.08 | 0.667 |
| 2012 | 30 | 0.3891 | 0.2828 | 0.9419 | 9.66 | 11.95 | 0.500 |
| 2013 | 28 | 0.1319 | 0.0899 | 0.9228 | 13.74 | 17.25 | 0.539 |
| **macro** | | **0.2860** | **0.2050** | **0.9370** | **12.39** | **15.43** | **0.568** |

**Macro Spearman 0.2860 against the development macro of 0.2968** — a difference of 0.011,
well inside the development fold SD of 0.124. MAE is slightly *better* (12.39 vs 13.21).

The methodology transfers backwards across the 2014 coverage break without retuning. This
is a genuine out-of-sample check: these years use a different data-coverage regime
(DATA.md §24.3) and were never seen by any selection decision. 2013 is weak (0.132),
consistent with the development window's own year-to-year spread. **No retuning was
performed after seeing these results.**

---

## 18. Selected Stage B methodology

**Target representation: `RAW_PICK`** — the pick number itself, unmodified.

Rationale:
- The four continuous targets are **statistically indistinguishable** (0.2596–0.2624 macro
  Spearman averaged over 12 models, against a fold SD of 0.13).
- Three of them are **provably rank-equivalent for a linear model** (rank correlation
  0.998), so choosing among them is choosing among labels, not methods.
- `LOG_PICK`, the only genuinely different target, is worse on NDCG, MAE, RMSE and
  worst-year, and its Spearman edge is a fortieth of the fold SD.
- Among rank-equivalent options, the tiebreak is interpretability and product safety:
  `RAW_PICK` is the most directly interpretable and is the **only one with no dependency on
  an externally maintained draft-size constant** — a dependency that was already wrong for
  2014 the first time it was checked (§4).

**Model: `Ridge(alpha=10)`** — see §8 for the full reasoning: inside noise of the best
macro Spearman, best fold SD of the ridge grid, and materially better coefficient stability
than the marginally higher-scoring α = 1.

**Frozen preprocessing** (inherited unchanged from Stage A, DEC-081):

| Step | Setting |
| --- | --- |
| Feature set | `SET_2_BOX_SHOT_PROFILE` (25 features) |
| Representation | `SEASON_RELATIVE` — z-score vs same-season, same-position NCAA reference |
| Missing data | Train-fold median imputation; no indicators; no complete-case deletion |
| Position | `position_3` one-hot (G / F / C / UNKNOWN) |
| Scaling | Train-fold `StandardScaler` |
| Target conditioning | Train-fold z-score of the target, exactly invertible and rank-preserving |
| Fitting | Everything refitted inside each fold; nothing shared across folds |

**Output contract:** Stage B emits a **`strength`** value where higher always means an
earlier predicted pick. This is the only orientation convention in the codebase; every
target is inverse-transformed to the pick scale before the sign is applied.

**Retained for display, not for ranking:** the `TIER_3` representation (lottery / rest of
first round / second round), at 42% exact and 79% adjacent accuracy.

---

## 19. Product-safe interpretation

**The numeric pick prediction must not be displayed.** §15 is unambiguous: MAE 13.3 picks,
21% within 5, predictions outside the legal range, and lottery-vs-second-round mean
predictions separated by under 6 picks. "Predicted Pick: 17.3" would assert precision the
model does not have, breaching PRODUCT.md §20 ("No fabricated data", "Decision support…
does not claim certainty") and ML_SPEC §17.2 ("No false precision").

Candidate display concepts, all supported by the evidence above — **the final UI decision
belongs to a later phase and is not made here**:

| Concept | Evidence support |
| --- | --- |
| **Relative draft order** (position on the board) | Strongest: Spearman positive in all 7 folds, beats every baseline |
| **Expected Draft Tier** (lottery / rest of R1 / round 2) | 79% adjacent-tier accuracy; matches how scouts speak |
| **Draft Range** (a band rather than a point) | Would need an interval method; residual spread suggests a band of roughly ±13 picks, which is wide enough that a tier may communicate better |
| **Draft Position Signal** (a normalised score) | Order-preserving by construction; defers to ML-6's Overall Score work |

Language that must **not** be used: "predicted pick", "projected to go 17th", or any
phrasing implying DraftLens forecasts the real NBA draft board — Stage B sees only NCAA
early entrants, not seniors or international prospects.

---

## 20. Rejected alternatives

| Alternative | Why rejected |
| --- | --- |
| `LOG_PICK` | The only genuinely non-affine transform; worse NDCG (0.9075 vs 0.9043 at equal α is within noise, but 0.8948 vs 0.9024 averaged over models), worse MAE (+0.6 picks), worst RMSE (17.31), worst worst-year (−0.101). Buys no rank quality. |
| `PICK_PERCENTILE` | Rank-equivalent to `RAW_PICK` (r = 0.998) so it wins nothing, and it adds a dependency on an external draft-size constant that was already wrong for 2014. |
| `DRAFT_VALUE` | Same rank-equivalence (r = 0.998) and same external dependency. Retained in the study only as the orientation check — it is the one target where higher means better. |
| Tier model as the **ranker** | Competitive (0.3036) but worst-year 0.0529 vs 0.1381, lower pooled Spearman, and cannot produce a pick-scale error. **Retained for display.** |
| Learning-to-rank | No clean sklearn estimator exists; installing a ranking library is prohibited. Ranking is the evaluation objective instead. Documented, not silently skipped. |
| Random forest (3 configs) | All below every ridge configuration on rank quality; best is 0.2661 vs 0.2968. |
| HistGradientBoosting (2 configs) | 0.2157–0.2504; `HGB_lr005_leaf4` has a near-zero worst year (0.0031). |
| Gradient boosting (1 config) | 0.2686 — the best nonlinear result, still 0.028 below the selected ridge. |
| ElasticNet (2 configs) | 0.1927–0.2646, the worst linear results. L1 selection within correlated groups is a liability (same as ML-4 §17). |
| `RIDGE_a1` | Marginally higher macro/pooled Spearman and NDCG, but the gap is a quarter of its own fold SD while coefficient volatility nearly doubles (fold SD 0.0747 vs 0.0388, 20/29 vs 22/29 sign-consistent). |
| `RIDGE_a50` / `a200` | α = 50 ties on macro but loses pooled Spearman (0.2996 vs 0.3252); α = 200 is over-regularised (worst year 0.0962). |
| `SET_2R_REDUCED` | Slightly worse on every axis (0.2910 vs 0.2968 macro, worse worst-year). Full set retained. |
| Four-tier scheme (1–14/15–30/31–45/46–60) | 8 of 48 year × tier cells below 5 members. Rejected on measured density, per ML_SPEC §6.3. |
| Selecting on RMSE | Explicitly prohibited, and §12 shows why: the whole field spans 13.1–14.4 MAE and a constant scores 14.02. |

---

## 21. Limitations

1. **The rank signal is modest.** Macro Spearman 0.2968 means pre-draft NCAA statistics
   explain a real but limited share of draft-order variation. Much of what determines
   draft position — workouts, interviews, medicals, team need, agent leverage, and
   scouting judgment — is not in this data and by design never will be.
2. **Year-to-year variation is ~40% of the signal** (fold SD 0.124 against macro 0.297).
   A single class can land anywhere between 0.14 and 0.49.
3. **Exact pick prediction is unusable** (§15) and this constrains the product.
4. **Lottery recall is only 54.5%** among in-scope early entrants — the model is weakest
   precisely at the top of the board, where scouting stakes are highest.
5. **Stage B sees only NCAA early entrants.** Not seniors, not international prospects.
   Board-level metrics must always carry that qualifier.
6. **Two coefficients are not individually interpretable** (`reb_per_40`, `usage_pct`) —
   §16.
7. **No uncertainty intervals.** Ridge gives none without distributional assumptions the
   data does not support. Residual spread is reported instead.
8. **Full-list NDCG discriminates poorly** at this population size (§13); Spearman and
   NDCG@14 carry the real information.
9. **2020 is the weakest fold** (0.138) and is a genuinely thinner statistical record
   (pandemic-shortened NCAA season), not merely a small sample.
10. **The draft-size table is externally maintained** and was found to contain an error on
    first inspection (§4). It is now validated against observed picks, but it remains a
    manual input for any future class.
11. **`TIER_3` at 42% exact accuracy** is a coarse instrument; adjacent-tier accuracy of
    79% is the honest headline, not the exact figure.

---

## 22. ML-6 recommendation

ML-6 combines Stage A and Stage B into the General Draft Board and Overall Score. **No part
of that is decided here.**

What ML-5 hands over:

- A **frozen Stage B ranking methodology** producing a `strength` signal with a single,
  tested orientation convention.
- A clear finding that **the Stage B signal is an ordering, not a pick**, which should
  shape how the Overall Score is constructed and displayed.
- The **`TIER_3` representation** as a display-ready, order-respecting summary.
- Evidence that **Stage B is the weaker of the two stages** — Stage A reaches macro
  ROC-AUC 0.6986 on a comparable scale of difficulty, while Stage B reaches Spearman
  0.2968. Any combination rule should not assume the two carry equal information.

Open questions ML-6 must resolve, none of which may be assumed:

- The Overall Score transformation, and whether it is class-relative or absolute
  (ML_SPEC §17 — still **unresolved**).
- How a calibrated `P(drafted)` and a conditional rank signal combine, given that Stage A
  ships uncalibrated (DEC-083) and Stage B is an ordering rather than a magnitude.
- Whether the board displays tiers, ranges, relative order, or a score — and with what
  language.
- Board-level evaluation (ML_SPEC §14) on the combined output.

Not touched by ML-5 and still out of scope: Team Need, archetypes, NBA comparables, the
web application, and the 2026 holdout.

The 2026 holdout remains sealed.
