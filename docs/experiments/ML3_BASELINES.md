# DraftLens — ML-3 Report: temporal baselines and preprocessing experiments

**Status:** Complete. **No production model approved; 2026 never touched.**
**Date:** 2026-08-08 · **Phase:** ML-3 ([ML_SPEC.md](../ML_SPEC.md) §27) · scikit-learn **1.9.0** · seed **20260808**

```bash
./.venv/bin/python scripts/experiments/ml3_baselines.py
./.venv/bin/python scripts/experiments/validate_ml3_baselines.py
./.venv/bin/python -m unittest discover -s tests
```

Configuration is version-controlled in [`config/ml/ml3_baselines.json`](../../config/ml/ml3_baselines.json). Companion documents: [ML_SPEC.md](../ML_SPEC.md), [ML2_FEATURES.md](ML2_FEATURES.md), [ML1_EDA.md](ML1_EDA.md).

---

## 1. Executive summary

Seven expanding-window folds, five ML_SPEC §15 baselines, 15 named logistic-regression configurations — **19 Stage A configurations in total**, plus the Stage B descriptive baseline. Validation: **0 hard failures**. **128 tests pass.**

**The headline is sobering and worth stating plainly: every configuration lands between macro ROC-AUC 0.669 and 0.698.** Separating drafted from undrafted *among declared early entrants* on NCAA box-score data is genuinely hard. That is an honest result, not a pipeline defect — the population is already pre-filtered to serious prospects, so the easy signal has been removed by construction.

**Three findings shape ML-4.**

1. **A heuristic matches the models.** `B4_POSITION_PERCENTILE_COMPOSITE` — an equal-weight composite of within-position percentile ranks — reaches **macro ROC-AUC 0.6943** with the **best stability of anything tested (SD 0.0219)** and the **best worst-year (0.6727)**. Regularised logistic regression spans 0.669–0.698. **ML-4 must beat ≈0.694 macro to justify any complexity.**
2. **But B4 cannot serve Stage A.** Its scores are rank quantiles, not probabilities: its calibration gap reaches **+0.22** (predicted 0.95 bin → 0.726 observed) and its Brier is **0.2530** against 0.226 for logistic regression. DEC-053 requires Stage A to output a calibrated `P(drafted)`. **B4 stays as the benchmark to beat, not the carry-forward.**
3. 🟠 **Coefficient instability is visible.** In the broadest feature set, `rim_make_pct` takes **+1.09** while the correlated `layup_make_pct` takes **−0.91** — a sign flip that is collinearity, not basketball. `tip_attempt_share` also draws **+0.57** despite a median of 0.009. This argues directly for the smaller, less collinear feature set.

**Selected for ML-4:** `LR | SET_2_BOX_SHOT_PROFILE | B_TRAIN_MEDIAN | STANDARD | ONEHOT | class_weight=balanced | C=1.0` — chosen on stability, worst-year behaviour, calibration and simplicity, **not** on peak AUC (§17).

## 2. Temporal folds

Expanding window; every transformer refitted inside each fold on training years only.

| Fold | Train | Train n | Validate | n | Drafted | Undrafted | Base rate |
| --: | --- | --: | --: | --: | --: | --: | --: |
| 1 | 2014–2018 | 270 | 2019 | 76 | 40 | 36 | 0.526 |
| 2 | 2014–2019 | 346 | 2020 | 65 | 40 | 25 | 0.615 |
| 3 | 2014–2020 | 411 | 2021 | 188 | 50 | 138 | 0.266 |
| 4 | 2014–2021 | 599 | 2022 | 132 | 43 | 89 | 0.326 |
| 5 | 2014–2022 | 731 | 2023 | 79 | 41 | 38 | 0.519 |
| 6 | 2014–2023 | 810 | 2024 | 49 | 33 | 16 | 0.673 |
| 7 | 2014–2024 | 859 | 2025 | 28 | 26 | **2** | 0.929 ⚠ **LOW NEGATIVE SUPPORT** |

All 887 development prospects participate, **including the 8 unresolved ones**, which receive train-fold median values rather than being dropped (DEC-071). Validation asserts that every eligible validation row receives a prediction.

## 3. Class balance

Base rate swings **0.266 → 0.929** across validation years. No year resembles the 0.486 aggregate, so pooled metrics are dominated by 2021 (188 rows, 21% of the window). This is why every result below is reported **both** year-macro and pooled.

## 4. Feature sets

| Set | n | Content |
| --- | --: | --- |
| `SET_0_MINIMAL` | 4 | points_per_40, minutes_per_game, ts_pct, height |
| `SET_1_BOX_EFFICIENCY` | 17 | box per-40 + efficiency + volume + usage + physicals |
| **`SET_2_BOX_SHOT_PROFILE`** | **25** | SET_1 + rim/layup/dunk shares, make rates, 3P%, unassisted creation |
| `SET_3_BROADER_CLEAN` | 38 | all de-duplicated ML-2 features |

Membership is fully enumerated in the config. `SET_2` deliberately **excludes the sparse ratios by construction**, so it is DEC-073-safe without needing an exclusion step.

## 5. Missing-data strategies

| Strategy | Result |
| --- | --- |
| **A — conservative exclusion** | Drop `tip_make_pct`, `dunk_make_pct`, `unassisted_dunk_make_share`, then train-fold median impute |
| **B — train-fold median** | Keep all, train-fold median impute |
| **B2 — position-aware median** | Medians within training-fold `position_3` |
| **C — high coverage only** | Only features ≥97% coverage in the training fold |

**No missingness indicators, no sentinels, no zero-filling, no row dropping** — all four are prohibited by DEC-073/DEC-071 and none was used.

**The A-vs-B comparison is only meaningful on SET_3**, because SET_2 contains none of the sparse features (A and B produce byte-identical results there — a useful confirmation the strategy switch works as intended). On SET_3:

| SET_3 configuration | macro ROC-AUC | Brier | SD | Worst year |
| --- | --: | --: | --: | --: |
| **A — exclusion**, balanced | **0.6979** | **0.2254** | 0.0512 | 0.6290 |
| B — impute, none | 0.6940 | 0.2320 | 0.0498 | 0.6329 |
| B — impute, balanced | 0.6915 | 0.2252 | 0.0480 | 0.6309 |

**Excluding the sparse ratios is at worst free and slightly better**, on top of removing the DEC-073 leakage risk. Exclusion is therefore adopted.

`B2` (position-aware median) and `C` (high coverage) both landed marginally *below* plain B on SET_2 (0.6820 and 0.6789 vs 0.6839) — neither earns its extra complexity.

## 6. Redundancy decisions

ML-2's 23 pairs at |r| ≥ 0.95 resolve into **14 connected groups**, of which 12 are recorded in the config with an explicit representative. The rule, applied uniformly and **never by validation AUC**:

1. For counting statistics prefer the **per-40 rate** — interpretable, comparable, with its denominator retained.
2. For algebraic complements keep the **unassisted** direction — self-creation is the meaningful basketball signal.
3. For attempt-mix complements keep **`three_point_attempt_rate`** (box-derived, independent of shot-file coverage).
4. Keep a possession percentage **only where it has no per-40 twin** — `usage_pct`, `tov_pct`.

| Group | Kept | Dropped |
| --- | --- | --- |
| blocks | `blocks_per_40` | blk_pct, blocks_per_100, blocks_per_game |
| assists | `assists_per_40` | ast_pct, assists_per_100, assists_per_game |
| attempt mix | `three_point_attempt_rate` | two_point_attempt_rate, three_point_shot_attempt_share |
| steals | `steals_per_40` | stl_pct, steals_per_100, steals_per_game |
| rebounds (O/D/T) | `oreb_per_40`, `dreb_per_40`, `reb_per_40` | orb_pct, drb_pct, trb_pct, rebounds_per_100, rebounds_per_game |
| points | `points_per_40` | points_per_100, points_per_game |
| turnovers | `turnovers_per_40` | turnovers_per_100, turnovers_per_game |
| creation (FG / layup / dunk) | `unassisted_*_share` | assisted_*_share |

A test asserts every dropped representation is absent from `SET_3` and every kept one is present.

## 7. Position handling

| Handling | macro ROC-AUC | SD | Worst year |
| --- | --: | --: | --: |
| **ONEHOT `position_3`** | **0.6839** | **0.0373** | **0.6431** |
| NONE | 0.6829 | 0.0486 | 0.6023 |

One-hot encoding is essentially neutral on average but **clearly better on stability (0.037 vs 0.049) and worst-year (0.643 vs 0.602)**. Retained. Only the coarse G/F/C scheme was used (DEC-067); no PG/SG/SF/PF/C label exists.

## 8. Preprocessing / scaling

| Scaling | macro ROC-AUC | SD | Worst year |
| --- | --: | --: | --: |
| **STANDARD** (train-fold fit) | **0.6839** | **0.0373** | **0.6431** |
| NONE | 0.6763 | 0.0520 | 0.5822 |

Standardisation matters for a regularised linear model — without it, penalty strength is arbitrary across differently-scaled features. The worst-year gap (0.643 vs 0.582) is the clearest evidence. Every scaler is fitted **inside the fold on training years only**; no global preprocessed dataset exists.

The season-relative variant was **not run**: with per-fold standardisation already applied and ML-2's reference distributions not yet joined to prospects, it would have duplicated Strategy B without isolating a season effect. Deferred to ML-4 with the reference artifact.

## 9. The five baselines

| # | Baseline | ML_SPEC §15 | macro ROC-AUC | macro Brier |
| --- | --- | --- | --: | --: |
| B0 | Constant training prevalence | (task-required floor) | 0.5000 | 0.2605 |
| B1 | Scoring average only | #1 | 0.5876 | 0.2949 |
| B2 | Standardised box-score composite | #2 | 0.6890 | 0.2623 |
| B3 | Logistic regression | #3 | 0.669–0.698 | 0.225–0.240 |
| **B4** | **Position-aware percentile composite** | **#4** | **0.6943** | 0.2530 |
| B5 | Naive mean pick by position (Stage B) | #5 | — | see §13 |

**B1 is barely better than chance (0.588)** — raw scoring alone carries little signal in a population already filtered to serious prospects. **B2 reaches 0.689 but is the least stable thing tested (SD 0.0811, worst year 0.5347)**. **B4 is the strongest and steadiest baseline**, which is itself the most important result of this phase.

## 10. Stage A fold results

Per-fold ROC-AUC for the three leading configurations:

| Year | B4 percentile composite | LR SET_2 balanced | LR SET_3 exclusion balanced |
| --- | --: | --: | --: |
| 2019 | 0.694 | 0.733 | **0.766** |
| 2020 | 0.713 | 0.669 | 0.696 |
| 2021 | **0.732** | 0.663 | 0.675 |
| 2022 | 0.696 | 0.698 | 0.722 |
| 2023 | 0.673 | 0.646 | **0.629** |
| 2024 | 0.680 | 0.646 | 0.648 |
| 2025 ⚠ | 0.673 | 0.712 | 0.750 |

B4 never drops below 0.673. Both LRs dip to ≈0.63–0.65 in 2023–2024.

## 11. Macro vs pooled

| Configuration | macro ROC-AUC | pooled ROC-AUC | macro PR-AUC | macro Brier | SD | Worst |
| --- | --: | --: | --: | --: | --: | --: |
| LR SET_3 exclusion balanced | **0.6979** | 0.6925 | 0.7114 | 0.2254 | 0.0512 | 0.6290 |
| **B4 percentile composite** | 0.6943 | 0.6759 | **0.7203** | 0.2530 | **0.0219** | **0.6727** |
| LR SET_3 median none | 0.6940 | 0.6755 | 0.7106 | 0.2320 | 0.0498 | 0.6329 |
| LR SET_2 none C=0.1 | 0.6931 | 0.6696 | 0.7073 | 0.2287 | 0.0396 | 0.6329 |
| B2 standardised composite | 0.6890 | 0.6533 | 0.7069 | 0.2623 | 0.0811 | 0.5347 |
| **LR SET_2 balanced C=1.0** ← selected | 0.6809 | 0.6865 | 0.7002 | **0.2262** | 0.0339 | 0.6458 |

**Macro and pooled disagree**, exactly as ML_SPEC §11.3 anticipated: `LR SET_2 balanced` is 6th on macro but 3rd on pooled, because pooled weighting favours configurations that handle the large 2021 cohort. Neither ordering is reported alone.

**The macro spread across all 15 LR configurations is 0.029.** With 7 folds and 28–188 validation rows each, that is inside noise. No configuration is statistically distinguishable from another on AUC.

## 12. Calibration

Out-of-fold, development only, deciles.

| Configuration | Max \|gap\| | Brier | Reading |
| --- | --: | --: | --- |
| **LR SET_2 balanced** | **0.140** | **0.2262** | Mild over-confidence at the top |
| LR SET_3 exclusion balanced | 0.213 | 0.2254 | Noticeably worse at the top decile |
| B4 percentile composite | 0.224 | 0.2530 | Not a probability at all |
| B2 standardised composite | 0.285 | 0.2623 | Worst |

For B4 the top decile predicts 0.950 and observes **0.726**; the bottom predicts 0.050 and observes 0.210. That is expected — the rank-to-unit mapping is uniform by construction, so it *cannot* be calibrated. **Only the logistic models produce usable probabilities, which Stage A requires.**

No calibration method was fitted. ML_SPEC §12.2 asks calibration to be *observed* first; Platt/isotonic belong to ML-4.

## 13. Board-level metrics

Precision@K with K = the number actually drafted that year:

| Year | B4 | LR SET_2 balanced | LR SET_3 |
| --- | --: | --: | --: |
| 2019 | 0.650 | 0.675 | 0.675 |
| 2020 | 0.750 | 0.700 | 0.725 |
| **2021** | **0.460** | **0.420** | **0.400** |
| 2022 | 0.535 | 0.581 | 0.558 |
| 2023 | 0.683 | 0.610 | 0.610 |
| 2024 | 0.697 | 0.758 | 0.758 |
| 2025 ⚠ | 0.962 | 0.962 | 0.962 |

**2021 is the hardest board year** for every method (0.40–0.46) — the 138-prospect undrafted cohort makes the top of the board genuinely crowded. **2025's 0.962 is an artifact**: 26 of 28 prospects were drafted, so almost any ordering scores near-perfectly. Macro NDCG@drafted: B4 **0.7171**, LR SET_3 0.7029, LR SET_2 0.6974.

## 14. Coefficient sanity

Largest standardised coefficients, final fold, `LR SET_3 exclusion balanced`:

```
points_per_40             +1.17     tip_attempt_share      +0.57
rim_make_pct              +1.09     ts_pct                 +0.51
layup_make_pct            -0.91     position_3_UNKNOWN     -0.48
fga_per_40                -0.81     efg_pct                -0.47
```

`points_per_40` leading positively is basketball-sensible. **Two signals are not:**

- **`rim_make_pct` +1.09 against `layup_make_pct` −0.91.** These measure nearly the same thing; opposite signs of similar magnitude is the classic signature of collinear inputs splitting a coefficient, not a finding about basketball.
- **`tip_attempt_share` +0.57** on a feature whose median is 0.009 — roughly one shot in a hundred. ML-2 already flagged it as the strongest raw separator; a large weight on it is more likely noise-fitting than signal.

**These are not leakage** — no feature is target-derived, and the deny-list holds — but they are a strong argument for the smaller, less collinear `SET_2`, and for testing stronger regularisation in ML-4. Coefficients are reported as a **sanity check only**, never as causal claims, and were not used for feature selection.

## 15. COVID and 2025 sensitivity

**2021–2022** behave exactly as ML-1 predicted. 2021 has the lowest board precision of any year for every method and pulls pooled metrics toward configurations that handle a large negative class. Discrimination there (AUC 0.66–0.73) is *not* unusually poor — the class balance simply makes the board harder.

**2025 is flagged LOW NEGATIVE SUPPORT** and treated accordingly. With 2 undrafted prospects, its ROC-AUC (0.673–0.750) rests on 52 pairwise comparisons and its Precision@K is 0.962 for everything. **It was not allowed to influence the selection**, and the year-macro aggregate is reported alongside SD and worst-year precisely so a single flattering fold cannot dominate.

## 16. Robustness — 2011–2013

Applied **after** the development decision, purely as a secondary check. Trained on the full 2014–2025 window, validated on the earlier years.

| Year | n | Base rate | ROC-AUC | PR-AUC | Precision@drafted | NDCG |
| --- | --: | --: | --: | --: | --: | --: |
| 2011 | 39 | 0.692 | 0.682 | 0.845 | 0.741 | 0.798 |
| 2012 | 43 | 0.698 | 0.718 | 0.844 | 0.833 | 0.851 |
| 2013 | 43 | 0.651 | 0.677 | 0.849 | 0.679 | 0.766 |

**Discrimination holds up (0.677–0.718), in line with the development folds** — despite the 2014 coverage break. The higher PR-AUC simply reflects the higher base rate. These years did **not** inform any choice.

## 17. Chosen configuration for ML-4

> **`LR | SET_2_BOX_SHOT_PROFILE | B_TRAIN_MEDIAN | STANDARD | ONEHOT | class_weight=balanced | C=1.0`**

It is **not** the top macro-AUC configuration (0.6809 vs 0.6979). It was selected on the multi-criterion rule, where AUC differences are noise:

| Criterion | Why this configuration |
| --- | --- |
| Year-macro ranking | 0.6809 — within 0.017 of the best; indistinguishable at this sample size |
| Pooled | **0.6865 — 3rd best**, ahead of the macro leader |
| Brier / log loss | **0.2262 / 0.6430 — best or joint-best** |
| Temporal stability | **SD 0.0339 — best of any LR** (macro leader: 0.0512) |
| Worst-year | **0.6458 — best of any LR** (macro leader: 0.6290) |
| Calibration | **Max gap 0.140 — best of all configurations** |
| Simplicity | 25 features vs 38; the smaller, less collinear space §14 argues for |
| Leakage safety | Excludes the DEC-073 sparse ratios **by construction** |
| Class balance | `balanced` is principled given a 0.27→0.93 base-rate swing |

**Class weighting:** `balanced` costs ~0.003 macro AUC and buys a better Brier (0.2262 vs 0.2340) and better stability. Given ML_SPEC §4.3's warning that the 2026 holdout base rate (0.96) differs sharply from training (0.49), a model that is not tuned to one prevalence is the safer carry-forward. **Retained — but on calibration and stability grounds, not accuracy.**

## 18. Rejected alternatives

| Rejected | Reason |
| --- | --- |
| **B4 as the Stage A carry-forward** | Best ranker and steadiest, but produces rank quantiles, not probabilities (calibration gap 0.22). DEC-053 requires calibrated `P(drafted)`. **Retained as the benchmark ML-4 must beat.** |
| `SET_3_BROADER_CLEAN` | Highest macro AUC, but worst LR stability and worst-year, worse calibration, and visible coefficient sign-flips from collinearity |
| `SET_0` / `SET_1` | Materially less stable (SD 0.097 / 0.067) and weaker |
| B2 standardised composite | SD 0.0811, worst-year 0.5347 — least stable of all |
| `B2_POSITION_MEDIAN` imputation | No gain (0.6820 vs 0.6839) for added complexity |
| `C_HIGH_COVERAGE` | Slightly worse (0.6789); discards usable signal |
| No scaling | Worst-year collapses to 0.582 |
| No position feature | Stability and worst-year both degrade |
| Larger C grid / any search | Out of scope — this is a baseline phase |

## 19. Limitations

1. **All discrimination is modest (0.67–0.70).** Box-score data alone does not separate declared early entrants well. ML-4 should treat a large jump as suspicious rather than welcome.
2. **A heuristic matches the models**, so complexity has a high bar to clear.
3. **Fold sizes vary 4-fold** (28 to 188); no aggregate fully resolves this.
4. **2025 carries almost no classification information.**
5. **Collinearity destabilises coefficients**, limiting how far the linear model can be read explanatorily.
6. **Calibration is untested out-of-era** — the 2026 base rate is far outside the training range and was deliberately not examined.
7. **Season-relative normalisation was not tested** (§8); it remains open.
8. Stage B is untouched beyond the mandated descriptive baseline.

## 20. ML-4 recommendation

**Scope: STAGE A CANDIDATE MODELS ONLY.**

1. Carry the §17 configuration forward as the **incumbent**.
2. Treat **B4's macro ROC-AUC 0.6943 / NDCG 0.7171 as the bar** — a nonlinear model that fails to beat an equal-weight percentile composite is not worth its complexity.
3. Compare the ML_SPEC §16 nonlinear candidates (random forest, gradient boosting, HistGradientBoosting) on the **same folds, same metrics, same macro-and-pooled reporting**.
4. Test stronger regularisation and/or an explicit collinearity remedy for the linear model (§14).
5. Evaluate calibration methods (Platt, isotonic) **inside folds**.
6. Revisit season-relative normalisation using the ML-2 reference distributions.
7. **Do not touch 2026.** Freezing happens at ML-7; the holdout runs exactly once at ML-8.

### Stage B — descriptive baseline only (ML_SPEC §15 #5)

Naive mean historical pick by `position_3`, drafted prospects only, un-optimised:

| Year | n drafted | MAE (picks) | RMSE | Spearman |
| --- | --: | --: | --: | --: |
| 2019 | 40 | 15.63 | 18.39 | +0.099 |
| 2020 | 40 | 14.75 | 17.35 | −0.073 |
| 2021 | 50 | 15.30 | 17.87 | −0.120 |
| 2022 | 43 | 13.98 | 16.29 | −0.147 |
| 2023 | 41 | 13.38 | 16.14 | −0.228 |
| 2024 | 33 | 12.35 | 14.20 | −0.150 |
| 2025 | 26 | 13.39 | 15.61 | −0.247 |

**Position alone carries no usable pick signal** — Spearman is near zero and mostly *negative*, and MAE of 12–16 picks spans half a round. This is the floor Stage B must clear, and it confirms that the Stage B target-design question (ML_SPEC §6.3) genuinely needs its own phase. **No Stage B model was selected.**
