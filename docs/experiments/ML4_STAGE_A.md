# ML-4 — Stage A candidate models

**Phase:** ML-4 · Stage A model selection
**Scope:** historical development window **2014–2025 only**
**Status:** complete — Stage A methodology selected
**Reproduce:** `./.venv/bin/python scripts/experiments/ml4_stage_a_selection.py` then `./.venv/bin/python scripts/experiments/validate_ml4_stage_a.py`

> **2026 holdout firewall.** No 2026 target file was loaded. No 2026 probability,
> ranking, board or metric was produced. The word 2026 appears in this report only
> to describe the firewall itself. Enforced by
> [`scripts/experiments/validate_ml4_stage_a.py`](../../scripts/experiments/validate_ml4_stage_a.py) check 1
> and by `tests/test_ml4_stage_a.py::TestHoldoutFirewall`.

---

## 1. Executive summary

ML-4 asked one question: does a modest nonlinear or better-regularised model improve
Stage A beyond the ML-3 logistic incumbent **without** sacrificing temporal robustness,
calibration, interpretability or leakage safety?

**Answer: the model family does not change. The feature representation does.**

Twenty-three predeclared configurations across four families were evaluated on the same
seven temporal folds as ML-3. The selected configuration is

> **`LR | SET_2_BOX_SHOT_PROFILE | SEASON_RELATIVE | B_TRAIN_MEDIAN | ONEHOT | class_weight=balanced | C=0.25`**
> — evaluated uncalibrated.

Three findings drove this, and the second is the most important thing in the phase.

1. **Nonlinear models did not earn their place.** Random forest posted the highest
   year-macro ROC-AUC of anything tested (0.7090). That lead was an artifact of a
   single degenerate fold — see §9. It does not survive.
2. **The 2025 fold has two undrafted prospects and it was silently deciding the
   leaderboard.** Removing it moves `RF_dNone_leaf30` from rank 1 to rank 12.
   Every tree ensemble in the study loses ground; the selected linear model is one of
   only four candidates that *gains*.
3. **What helped was normalising each prospect against their own season's NCAA peer
   distribution — not model capacity.** The two best configurations overall are the
   season-relative logistic regression and the B4 within-position percentile
   composite. Both are linear-or-simpler. Both normalise against a peer reference.
   That is a mechanism, not a coincidence (§12).

Against the DEC-078 incumbent the selected model improves on **11 of 12** reported
measures, including every stability measure, while remaining the same model family with
the same 25 features and the same interpretability. The single measure it loses on —
max calibration gap — is traced in §13 to one anomalous decile, and the support-weighted
calibration error (ECE) is in fact **better** (0.0590 vs 0.0701).

It does **not** clear the DEC-079 benchmark decisively: B4 remains within 0.002 macro
ROC-AUC and beats it on NDCG. §14 states plainly what this does and does not license.

---

## 2. What ML-4 was not

Out of scope, and untouched:

- No 2026 prediction, probability, ranking, board or metric.
- No Stage B model, no draft-pick prediction.
- No Overall Score, no /100 score, no sub-scores.
- No Team Need, no archetypes, no NBA comparables.
- No web application.
- No XGBoost, LightGBM, CatBoost, Optuna, SHAP, MLflow, TensorFlow or PyTorch —
  scikit-learn only, asserted by
  `tests/test_ml4_stage_a.py::test_no_prohibited_gradient_boosting_dependency`.

This was not a leaderboard search. It was a test of whether complexity is warranted.

---

## 3. Selection design — and why not nested tuning

Recorded in [`config/ml/stage_a.json`](../../config/ml/stage_a.json) as
`PREDECLARED_FIXED_CONFIGURATIONS`.

Every one of the 23 configurations was written into the config file **before any outer-fold
result was inspected**, and all 23 were evaluated identically on all 7 folds. Nothing was
added, removed or retuned afterwards. `validate_ml4_results.py` check 8 fails if the set
of configurations evaluated differs from the set declared.

Nested temporal tuning was considered and rejected. There are only 7 outer folds, and the
earliest trains on 5 years / 270 rows. An inner temporal split inside that would leave
roughly 2–3 years and ~150 rows to choose a configuration from — far too noisy to select
on — and the resulting choice would then be reported as if it had been unbiased. A small
predeclared grid is the honest option at this sample size.

**Random K-fold CV is not used anywhere in ML-4.** It would mix draft years and destroy
the temporal guarantee. `no_random_cv: true` is asserted in the config and tested.

---

## 4. Temporal folds — unchanged from ML-3

Seven expanding-window folds, training always strictly earlier than validation:

| Fold | Train | Validate | n | Drafted | Undrafted | Base rate | Flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2014–2018 | 2019 | 76 | 40 | 36 | 0.526 | |
| 2 | 2014–2019 | 2020 | 65 | 40 | 25 | 0.615 | |
| 3 | 2014–2020 | 2021 | 188 | 50 | 138 | 0.266 | COVID cohort |
| 4 | 2014–2021 | 2022 | 132 | 43 | 89 | 0.326 | |
| 5 | 2014–2022 | 2023 | 79 | 41 | 38 | 0.519 | |
| 6 | 2014–2023 | 2024 | 49 | 33 | 16 | 0.673 | |
| 7 | 2014–2024 | 2025 | 28 | 26 | **2** | 0.929 | **LOW NEGATIVE SUPPORT** |

617 out-of-fold predictions per configuration. 2019–2025 are validated; 2014–2018 serve
only as training history. The full development population is 887.

---

## 5. Development population — unchanged and complete

**887 prospects · 431 drafted · 456 undrafted.** Identical to ML-0.1, ML-2 and ML-3.

- No prospect was dropped for missing basketball statistics.
- No complete-case deletion anywhere in the pipeline.
- The **8 unresolved prospects** (no hoopR match) are retained; the 5 of them falling in
  validated years received predictions from every configuration.
- No missingness indicator columns were added (DEC-069, DEC-073).
- Missing values are filled with **train-fold medians only** — validation values never
  influence a fill value.

Checks 5 and 6 of the validator enforce all of this, per configuration and per fold:
every configuration produced exactly 617 predictions, all finite, all within [0, 1].

---

## 6. Feature sets

**`SET_2_BOX_SHOT_PROFILE` — 25 features, inherited unchanged from ML-3.** Excludes the
DEC-076 sparse rare-event ratios by construction.

**`SET_2R_REDUCED` — 21 features.** Four removed for *mathematical* redundancy measured
before any model was fitted, never by validation score:

| Removed | Reason |
| --- | --- |
| `rim_attempt_share` | **Exact** linear combination of layup + dunk + tip attempt shares — max deviation 0.0000000000 |
| `efg_pct` | \|r\| = 0.939 with `ts_pct`, which is strictly more complete (includes free throws) |
| `fg_pct` | \|r\| = 0.856 with `efg_pct`, 0.792 with `ts_pct`; fully subsumed |
| `layup_make_pct` | \|r\| = 0.821 with `rim_make_pct`; ML-3 fitted them at +1.09 / −0.91, a collinearity sign flip |

An exact linear combination among the inputs makes the logistic solution non-unique in
that subspace, which is why `rim_attempt_share` is a structural problem rather than a
statistical preference.

The reduced set is tested to be a strict subset, and each removal is tested to carry a
structural justification rather than a performance one.

No denied feature entered X in any configuration: no `position_from_population`,
`class_from_population`, `match_method`, `match_confidence`, `population_source`,
`early_entrant`, age/DOB, PG/SG/SF/PF/C, generic `jump_shot_*`, identity column or target
field. Position enters only as `position_3` (coarse G/F/C/UNKNOWN from hoopR), the one
leakage-safe source (DEC-067). Verified on the feature lists *and* on the fitted model's
coefficient index.

---

## 7. The 23 predeclared candidates

| Family | Configurations |
| --- | --- |
| **Logistic regression** (15) | L2 at C ∈ {0.05, 0.1, 0.25, 0.5, 1.0}; unweighted at C ∈ {0.25, 1.0}; reduced set at C ∈ {0.1, 0.25, 1.0}; L1 at C ∈ {0.1, 1.0}; season-relative at C ∈ {0.25, 1.0}; season-relative + reduced at C = 0.25 |
| **Random forest** (3) | depth 4 / leaf 20 · depth 6 / leaf 10 · unlimited depth / leaf 30 — all 500 trees, `max_features="sqrt"` |
| **HistGradientBoosting** (3) | lr 0.05 / 8 leaves · lr 0.05 / 4 leaves / L2 = 5.0 · lr 0.1 / 8 leaves unweighted |
| **Classic gradient boosting** (2) | depth 2 · depth 3 — both lr 0.05, 200 estimators, subsample 0.8 |

Plus `B4_BENCHMARK`, the DEC-079 standing benchmark, recomputed from ML-3 code.

All tree ensembles were given `class_weight="balanced"` where the estimator supports it,
matching the incumbent's treatment, so the class-weight policy is not a confound between
families.

---

## 8. Results — headline ranking

Sorted by year-macro ROC-AUC (**the naive view — §9 corrects it**):

| Config | Family | macro AUC | pooled AUC | Brier | NDCG | fold SD | worst year | ECE |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RF_dNone_leaf30 | RF | **0.7090** | 0.6860 | 0.2242 | 0.7061 | 0.0755 | 0.6500 | 0.0780 |
| LR_R_SEASONREL_C0.25 | LR | 0.7072 | 0.6895 | 0.2230 | 0.7035 | 0.0452 | 0.6592 | 0.0770 |
| RF_d6_leaf10 | RF | 0.7062 | 0.6943 | 0.2217 | 0.7127 | 0.0652 | 0.6231 | 0.0804 |
| RF_d4_leaf20 | RF | 0.7033 | 0.6887 | 0.2243 | 0.7149 | 0.0737 | 0.6345 | 0.0755 |
| LR_R_C0.1 | LR | 0.6994 | 0.6895 | 0.2212 | 0.6939 | 0.0670 | 0.5988 | 0.0493 |
| **LR_SEASONREL_C0.25** | **LR** | **0.6986** | **0.6953** | **0.2238** | **0.7061** | **0.0281** | **0.6742** | **0.0590** |
| LR_C0.05 | LR | 0.6985 | 0.6943 | 0.2190 | 0.7058 | 0.0433 | 0.6297 | 0.0409 |
| GB_d3_lr005 | GB | 0.6982 | 0.6742 | 0.2401 | 0.6947 | 0.0488 | 0.6320 | 0.1130 |
| HGB_lr005_leaf4 | HGB | 0.6972 | 0.6943 | 0.2223 | 0.6939 | 0.0542 | 0.6140 | 0.0787 |
| B4_BENCHMARK | heuristic | 0.6943 | 0.6759 | 0.2530 | **0.7171** | **0.0219** | 0.6727 | 0.1371 |
| LR_C1.0_INCUMBENT | LR | 0.6809 | 0.6865 | 0.2262 | 0.6974 | 0.0339 | 0.6458 | 0.0701 |

Full table: `data/interim/ml4/model_comparison.csv` (git-ignored).

Two things are already visible. The whole field spans **0.681–0.709 macro AUC** — a
0.028 range across four model families and 23 configurations. And the tree ensembles that
top the table have the *worst* fold SDs in the study (0.065–0.076, against the incumbent's
0.034). Both are warnings.

---

## 9. The finding that decided the phase — low negative support

The 2025 fold validates on 28 prospects of whom **exactly 2 are undrafted**. An ROC-AUC
computed against 2 negatives is close to noise: it can take only a small number of
distinct values, and it carries a full 1/7 of every year-macro average.

DEC-075 already requires such folds to be flagged and to not drive selection. ML-4 makes
that operational by re-ranking with the fold removed:

| Config | macro (all 7) | macro (excl. 2025) | **shift** | SD excl. | worst excl. |
| --- | --- | --- | --- | --- | --- |
| **LR_SEASONREL_C0.25** | 0.6986 | **0.6997** | **+0.0011** | 0.0307 | **0.6742** |
| B4_BENCHMARK | 0.6943 | 0.6978 | +0.0035 | 0.0217 | 0.6727 |
| LR_R_SEASONREL_C0.25 | 0.7072 | 0.6969 | −0.0103 | 0.0394 | 0.6592 |
| LR_SEASONREL_C1.0 | 0.6869 | 0.6925 | +0.0056 | 0.0365 | 0.6477 |
| LR_C0.05 | 0.6985 | 0.6899 | −0.0086 | 0.0404 | 0.6297 |
| RF_d6_leaf10 | 0.7062 | 0.6861 | −0.0201 | 0.0413 | 0.6231 |
| HGB_lr005_leaf4 | 0.6972 | 0.6852 | −0.0120 | 0.0482 | 0.6140 |
| GB_d3_lr005 | 0.6982 | 0.6832 | −0.0150 | 0.0310 | 0.6320 |
| **RF_dNone_leaf30** | **0.7090** | **0.6830** | **−0.0260** | 0.0338 | 0.6500 |
| RF_d4_leaf20 | 0.7033 | 0.6795 | −0.0238 | 0.0419 | 0.6345 |
| LR_C1.0_INCUMBENT | 0.6809 | 0.6758 | −0.0051 | 0.0340 | 0.6458 |

`RF_dNone_leaf30` scored **0.8654 on the 2-negative fold** and 0.6830 on average
everywhere else. It moves from **rank 1 to rank 12**. All three random forests and both
gradient-boosting configurations show the same pattern: their advantage is concentrated in
the one fold that cannot support the measurement.

**The four largest negative shifts in the entire study all belong to tree ensembles.**
The four positive shifts belong to B4 and the three season-relative logistic models.

This is the clearest possible statement of the ML-4 verdict: the nonlinear advantage was
not real.

---

## 10. Fold-paired comparison

Per-fold differences against the incumbent — with 7 folds, the spread of the difference
matters more than its mean:

| Config | mean Δ | SD of Δ | wins | losses | worst fold Δ |
| --- | --- | --- | --- | --- | --- |
| RF_dNone_leaf30 | +0.0281 | 0.0610 | 4 | 3 | −0.0209 |
| LR_R_SEASONREL_C0.25 | +0.0263 | 0.0311 | 6 | 1 | −0.0258 |
| RF_d6_leaf10 | +0.0253 | 0.0468 | 5 | 2 | −0.0227 |
| **LR_SEASONREL_C0.25** | **+0.0177** | **0.0256** | **5** | **2** | **−0.0192** |
| LR_C0.05 | +0.0176 | 0.0253 | 5 | 2 | −0.0196 |
| B4_BENCHMARK | +0.0134 | 0.0415 | 4 | 3 | −0.0395 |

**Stated plainly: no candidate's improvement exceeds its own fold-to-fold spread.** For
the selected model the mean gain (+0.0177) is smaller than the SD of that gain (0.0256).
On 7 folds this is not a statistically decisive result and must not be reported as one.

What the selected model does have is *consistency of direction*: it wins 5 of 7 folds, its
worst fold costs only 0.019, it improves rather than degrades when the degenerate fold is
removed, and it has the best worst-year of any candidate. That is the basis for preferring
it — not significance.

Per-fold ROC-AUC of the selected model against the incumbent:

| Year | Incumbent | Selected | Δ |
| --- | --- | --- | --- |
| 2019 | 0.7333 | 0.7576 | +0.0243 |
| 2020 | 0.6690 | 0.6980 | +0.0290 |
| 2021 | 0.6626 | 0.6759 | +0.0133 |
| 2022 | 0.6979 | 0.6888 | −0.0091 |
| 2023 | 0.6463 | 0.7035 | +0.0572 |
| 2024 | 0.6458 | 0.6742 | +0.0284 |
| 2025 † | 0.7115 | 0.6923 | −0.0192 |

† LOW NEGATIVE SUPPORT — excluded from selection reasoning.

---

## 11. Year-macro vs pooled (DEC-075)

Both reported, always. For the selected model they agree, which is itself reassuring:
macro **0.6986**, pooled **0.6953** — and the pooled figure is the **highest of any
configuration in the study**, including every tree ensemble. The incumbent's macro/pooled
gap (0.6809 / 0.6865) was wider.

One caveat that matters for reading the tables: for the *calibrated* variants the pooled
AUC collapses (e.g. `RF_d6_leaf10+sigmoid` pooled 0.5715 against macro 0.6982). This is an
artifact of the evaluation protocol, not a property of the models — each fold fits its own
calibrator, so the seven years' probabilities land on seven different scales and pooling
them across years destroys comparability. In deployment only one draft year is scored at a
time, so this effect would not arise. Year-macro is the correct aggregation for calibrated
models.

---

## 12. Season-relative normalisation — what it is and why it is safe

Ten metrics (`points_per_40`, `reb_per_40`, `assists_per_40`, `steals_per_40`,
`blocks_per_40`, `ts_pct`, `efg_pct`, `three_point_attempt_rate`, `free_throw_rate`,
`minutes_per_game`) are replaced by their z-score against the NCAA reference distribution
for the **same season and same coarse position**, built in ML-2 from the full hoopR NCAA
player population. The remaining 15 features are unchanged, and the train-fold
`StandardScaler` still runs afterwards.

**Leakage analysis.** Three separate questions, all answered:

1. *Does the reference contain draft outcome?* No. It is built from the entire NCAA player
   population of that season — tens of thousands of players, the overwhelming majority of
   whom are not prospects — and `build_reference()` never reads a target. This is
   important: it is **not** the prospect sampling frame, so it cannot reintroduce the
   sampling-frame leakage channel that ML-1 identified.
2. *Does it use future information?* No. Season Y prospects are normalised against
   season Y, whose games conclude in March/April, before the June draft. This satisfies
   ML_SPEC §9.2 — the statistic is available before the evaluated draft. Season Y+1 is
   never consulted for a season Y prospect.
3. *Is it applied asymmetrically?* No. The identical formula is applied to every draft
   year, in training and validation alike.

Tested: only the covered metrics are rewritten, row count and identity are preserved, and
the transform is deterministic.

**Why it works.** The NCAA environment drifts across 2014–2025 — pace, three-point volume,
and the 2021 COVID cohort all move the raw scales, which ML-1 flagged. Raw per-40 figures
are therefore not comparable across the window, and a model trained on 2014–2018 raw
scales is partly fitting an era rather than a player. Z-scoring against the contemporaneous
peer distribution removes that drift.

The corroborating evidence is that **B4 — the within-position percentile composite — is the
other top performer**, and it is a 6-metric heuristic with no fitted coefficients at all.
Two methods with nothing in common except peer-relative normalisation both beat every raw-scale
model. The signal is the normalisation, not the model.

---

## 13. Calibration

Three methods compared — none, sigmoid (Platt), isotonic — under **`TEMPORAL_HOLDOUT`**:
the base model is fitted on every training year *except the last*, the calibrator is fitted
on that final held-out training year only, and the calibrated model then predicts the outer
validation year. sklearn's `CalibratedClassifierCV` default is random K-fold, which would
mix draft years; it is deliberately not used. All **56** calibrator fits are verified
strictly earlier than their validation year.

A control was added — `+none_reduced`, the same shortened base fit with no calibrator —
because otherwise an AUC change under calibration cannot be distinguished from the cost of
surrendering a training year.

| Config | macro AUC | Brier | log loss | max gap | **ECE** | p range |
| --- | --- | --- | --- | --- | --- | --- |
| **LR_SEASONREL_C0.25** | **0.6986** | 0.2238 | 0.6350 | 0.1965 | **0.0590** | 0.001–0.982 |
| … + none_reduced (control) | 0.6889 | 0.2293 | 0.6473 | 0.1922 | 0.0954 | 0.001–0.989 |
| … + sigmoid | 0.6889 | **0.2209** | **0.6325** | **0.1427** | 0.0714 | 0.136–0.752 |
| … + isotonic | 0.6826 | 0.2243 | 0.8361 | 0.2829 | 0.1419 | 0.000–1.000 |
| LR_C1.0_INCUMBENT | 0.6809 | 0.2262 | 0.6430 | 0.1395 | 0.0701 | 0.001–0.981 |
| … + sigmoid | 0.6716 | 0.2236 | 0.6384 | 0.1569 | 0.0925 | 0.145–0.750 |

**Decision: ship uncalibrated.** Three reasons.

1. **The AUC cost of calibration is not a calibration effect.** `+sigmoid` and
   `+none_reduced` produce *identical* AUC, NDCG and fold SD — sigmoid is monotone, so it
   cannot reorder the board. The entire −0.0097 is the surrendered training year. Tested
   directly (`test_sigmoid_is_rank_preserving`).
2. **The uncalibrated model is already the best-calibrated logistic model on ECE.** Its
   max gap of 0.1965 comes from a single decile (bin 8: 0.7127 predicted vs 0.5161
   observed) while its neighbours sit at 0.0015 and 0.0789. Support-weighted across all
   deciles it scores **0.0590**, better than its own sigmoid variant (0.0714) and better
   than the incumbent (0.0701). Max gap alone was misleading here, which is why ECE was
   added.
3. **Sigmoid compresses the usable probability range from 0.98 to 0.62**, capping the top
   of the board at p = 0.752. A draft tool that cannot express "this prospect is a
   near-certain pick" has lost something real.

**Isotonic is rejected outright** for every finalist: log loss degrades to 0.84–0.88 and
ECE roughly doubles. A nonparametric calibrator fitted on one year of 49–188 rows overfits,
exactly as sample size predicts.

Sigmoid remains available and is not ruled out for later phases — against its *own* control
it does improve Brier, log loss and max gap. If a future phase needs tighter probabilities
more than it needs the training year, it is the method to use. Isotonic is not.

---

## 14. Against the DEC-079 benchmark

DEC-079 set the bar: a more complex model must beat **macro ROC-AUC 0.6943** and
**macro NDCG@drafted 0.7171**.

| | B4 benchmark | Selected | Verdict |
| --- | --- | --- | --- |
| macro ROC-AUC | 0.6943 | 0.6986 | +0.0043 — **not decisive** |
| macro ROC-AUC excl. low-support | 0.6978 | 0.6997 | +0.0019 — **not decisive** |
| macro NDCG@drafted | **0.7171** | 0.7061 | **−0.0110 — benchmark wins** |
| Brier | 0.2530 | **0.2238** | selected wins clearly |
| ECE | 0.1371 | **0.0590** | selected wins clearly |
| fold SD | **0.0219** | 0.0281 | benchmark wins |
| worst year | 0.6727 | **0.6742** | +0.0015 — a tie |

**Honest verdict: the selected model does not beat B4 on ranking.** B4 remains the better
pure ranker, as DEC-079 anticipated, and its stability is still the best in the project.

The selected model is carried forward anyway, and the reason is not performance: DEC-053
requires Stage A to emit a **calibrated `P(drafted)`**, and B4 emits rank quantiles. On
that requirement the gap is not close — Brier 0.2238 vs 0.2530 and ECE 0.0590 vs 0.1371.
B4 cannot fill the Stage A role no matter how well it ranks.

**DEC-079 therefore stands unchanged.** B4 remains the standing benchmark, and it remains
un-beaten on NDCG. Any future Stage A work still has to clear it.

---

## 15. Interpretability — coefficients

Fitted on the full 2014–2025 development window, with per-fold sign consistency across all
7 folds. **22 of 29 terms are sign-consistent.**

| Feature | Full window | Sign-consistent | Fold SD |
| --- | --- | --- | --- |
| `rim_make_pct` | **+0.635** | yes | 0.157 |
| `layup_make_pct` | **−0.583** | yes | 0.063 |
| `layup_attempt_share` | **−0.574** | yes | 0.129 |
| `assists_per_40` | +0.417 | yes | 0.047 |
| `ts_pct` | +0.417 | yes | 0.079 |
| `rim_attempt_share` | +0.412 | **no** | 0.209 |
| `position_3=UNKNOWN` | −0.398 | yes | 0.062 |
| `minutes_per_game` | +0.366 | yes | 0.027 |
| `start_share` | −0.332 | yes | 0.048 |
| `steals_per_40` | +0.303 | yes | 0.115 |
| `blocks_per_40` | +0.285 | yes | 0.033 |
| `points_per_40` | +0.238 | **no** | 0.152 |
| `fg_pct` | −0.197 | **no** | 0.289 |
| `reb_per_40` | +0.194 | yes | 0.058 |
| `three_point_pct` | +0.180 | yes | 0.040 |
| `turnovers_per_40` | −0.144 | yes | 0.130 |
| `usage_pct` | +0.023 | **no** | 0.179 |

Full table: `data/interim/ml4/selected_model_coefficients.csv`.

**Basketball reading.** Finishing efficiency at the rim, playmaking, true shooting, minutes
played, steals and blocks all push draft probability up; turnovers push it down. An
UNKNOWN position label is a meaningful negative — a prospect hoopR could not classify is
typically a lower-profile player. That is a coherent scouting story.

**The caveat, stated clearly.** The collinear cluster is still present and its coefficients
are **not individually interpretable**. `rim_make_pct` at +0.64 alongside `layup_make_pct`
at −0.58 is a collinearity sign flip, not a finding that missing layups helps a prospect;
the pair correlates at \|r\| = 0.821 and only their *joint* contribution is meaningful. The
same applies to `rim_attempt_share` / `points_per_40` / `fg_pct` / `usage_pct` — which are
exactly the terms whose signs are not fold-stable, and exactly the terms `SET_2R` removes.

This is the strongest argument against the selected configuration and it is recorded as
such: the reduced set `LR_R_SEASONREL_C0.25` fixes the interpretability problem, and it
scored higher on the naive ranking (0.7072). It was not selected because it is *worse* on
the low-support-robust ranking (0.6969 vs 0.6997), worse on ECE (0.0770 vs 0.0590), worse
on fold SD (0.0394 vs 0.0307) and worse on worst-year (0.6592 vs 0.6742). Explainability
work in a later phase must present these coefficients as a group, or revisit the reduced
set with the evidence available then.

---

## 16. Class weighting

`class_weight="balanced"` is retained, and the evidence is unchanged from DEC-078.

| | macro AUC | macro excl. low | Brier | ECE |
| --- | --- | --- | --- | --- |
| `LR_C0.25` balanced | 0.6891 | 0.6822 | **0.2224** | **0.0722** |
| `LR_C0.25` unweighted | 0.6901 | **0.6833** | 0.2305 | 0.0988 |
| `LR_C1.0` balanced (incumbent) | 0.6809 | 0.6758 | **0.2262** | **0.0701** |
| `LR_C1.0` unweighted | 0.6839 | **0.6761** | 0.2340 | 0.0957 |

Unweighted is marginally better on ranking (+0.001 macro) and clearly worse on probability
quality (Brier +0.008, ECE +0.026 at both C values). Since Stage A's product obligation is a
calibrated probability, the trade favours `balanced`. This also matters for a reason
specific to this project: ML_SPEC §4.3 records that the eventual holdout base rate sits far
outside the training range, so probability quality under class imbalance is not an academic
concern.

---

## 17. Regularisation

C = 0.25 was selected. The regularisation path on the standard representation is
informative in its own right:

| C | macro AUC | macro excl. low | Brier | ECE | max gap |
| --- | --- | --- | --- | --- | --- |
| 0.05 | 0.6985 | 0.6899 | **0.2190** | **0.0409** | **0.0908** |
| 0.1 | 0.6935 | 0.6873 | 0.2201 | 0.0619 | 0.1022 |
| 0.25 | 0.6891 | 0.6822 | 0.2224 | 0.0722 | 0.1286 |
| 0.5 | 0.6867 | 0.6794 | 0.2244 | 0.0640 | 0.1425 |
| 1.0 (incumbent) | 0.6809 | 0.6758 | 0.2262 | 0.0701 | 0.1395 |

**Stronger regularisation improves discrimination and Brier monotonically** across all five
values on the raw representation, and improves calibration broadly though not monotonically
(ECE dips at C = 0.5). `LR_C0.05` has the best ECE (0.0409) and best max gap (0.0908) of
anything in the study. That is a real finding and it is the direction a future phase should
push.

It was not selected because its worst-year (0.6297) and low-support-robust macro (0.6899)
are both materially below the season-relative model's, and worst-year robustness is the
criterion this project has consistently prioritised. Note also that the season-relative
representation prefers a *different* C than the raw one — 0.25 rather than 0.05 — which is
consistent with z-scored inputs already carrying part of the regularising effect.

L1 was tested at C ∈ {0.1, 1.0} and rejected: both rank below the incumbent on the
low-support-robust ranking (0.6694 and 0.6788), and `LR_L1_C0.1` has the second-worst shift
of any logistic model. At 25 correlated features, L1's arbitrary selection within a
correlated group is a liability rather than a simplification.

---

## 18. What would have happened under a naive protocol

Worth recording, because it is the phase's methodological lesson. A study that had:

- ranked on year-macro ROC-AUC alone,
- not flagged low negative support,
- not run the calibration control,

would have selected **`RF_dNone_leaf30`** at 0.7090 and reported a +0.028 improvement over
the incumbent. That model is 12th once the 2-negative fold is removed, has the worst fold SD
in the study (0.0755), is not interpretable, and its headline gain came from a fold with two
negative examples.

The guards that caught this — DEC-075's low-support flag, the macro/pooled dual reporting
requirement, and the multi-criterion rule from DEC-078 — were all put in place in earlier
phases before this result existed. They earned their keep here.

---

## 19. Limitations

1. **The improvement is not statistically decisive.** Mean paired gain +0.0177 against a
   fold SD of 0.0256 on 7 folds. The case rests on directional consistency and robustness,
   not significance. §10.
2. **All Stage A models remain clustered in a narrow band** — 0.681–0.709 macro AUC across
   four families. The ceiling is set by the available features, not the algorithm. Whether
   NCAA box-score and shot-profile data can separate drafted from undrafted prospects much
   better than this is an open question ML-4 does not answer.
3. **The selected model does not beat B4 on ranking** (§14).
4. **Coefficients in the collinear cluster are not individually interpretable** (§15).
5. **One fold in seven cannot support an AUC measurement.** 2025 is reported but excluded
   from selection reasoning throughout.
6. **2021 is a COVID cohort** with 188 prospects at a 0.266 base rate — 30% of the
   out-of-fold predictions come from an anomalous year.
7. **Calibration was studied on four finalists, not all 23** — those finalists were chosen
   using the low-support-robust ranking, which is itself derived from outer-fold results.
   This is disclosed rather than hidden; it affects which models were calibrated, not any
   reported metric.
8. **`three_point_pct` and other rate features remain unstable for low-volume shooters** —
   inherited from ML-2, not addressed here.
9. **No 2026 evidence exists** and none was sought. Nothing in this report should be read
   as predicting how the selected model will perform on the holdout.

---

## 20. Reproducibility

- Seed **20260808** on every estimator; asserted by test for all 23 candidates.
- `validate_ml4_results.py` **re-executes the entire pipeline** and requires every fold
  metric to match to 6 decimal places. It does.
- The ML-3 anchors are re-derived from scratch each run and checked against DEC-078 and
  DEC-079 to 5e-4: **B4 macro 0.6943 / NDCG 0.7171 / SD 0.0219 / worst 0.6727** and
  **incumbent macro 0.6809 / pooled 0.6865 / Brier 0.2262 / SD 0.0339 / worst 0.6458**.
  Both reproduced exactly. ML-3 remains valid.
- **163 tests pass** (128 pre-existing + 35 new); no pre-existing test was modified.
- All generated artifacts are git-ignored and verified untracked by validator check 11.

One environment note: scikit-learn 1.9 deprecates the `penalty` argument in favour of
`l1_ratio`. `make_estimator` translates it, verified equivalent — `l1_ratio=0.0` reproduces
`penalty="l2"` coefficients to 0.0 difference, and `l1_ratio=1.0` reproduces `penalty="l1"`
sparsity exactly (17/25 zero coefficients in both cases). The config keeps the readable
`penalty` name and a test asserts the translation does not mutate it.

---

## 21. Artifacts

Written to `data/interim/ml4/` — **git-ignored, none committed**:

| File | Contents |
| --- | --- |
| `candidate_results.csv` | 252 rows — every config × fold, all metrics |
| `model_comparison.csv` | Aggregated macro + pooled per config |
| `outer_fold_predictions.parquet` | 617 out-of-fold predictions per config |
| `calibration_results.csv` | 56 calibrator fits with temporal-ordering proof |
| `low_support_sensitivity.csv` | The §9 re-ranking |
| `paired_vs_incumbent.csv` | The §10 fold-paired differences |
| `selected_model_coefficients.csv` | Per-fold + full-window coefficients |
| `ml4_summary.json` | Machine-readable run summary |

No trained model was serialised. No predictions were committed.

---

## 22. What ML-5 must decide

Not decided here, and not to be assumed:

- **Stage B** — model family, target design, tier boundaries. Untouched.
- **Overall Score** — the transformation, and whether it is class-relative or absolute.
- **Team Need, archetypes, NBA comparables** — all untouched.
- **Explainability method** for the selected model, given §15's collinearity caveat.
- **Whether to revisit `SET_2R`** with the ML-4 evidence now available.
- **Whether stronger regularisation on the season-relative representation** helps —
  §17 shows C = 0.05 dominates on the raw representation, but no season-relative
  configuration below C = 0.25 was predeclared, and adding one now would be post-hoc
  selection. It must be predeclared in a future phase.
- **Whether 2011–2013 enter training** or remain robustness-only.
- **Sigmoid calibration** may be reconsidered if a later phase values probability
  tightness above the surrendered training year. Isotonic should not be.

The 2026 holdout remains sealed.
