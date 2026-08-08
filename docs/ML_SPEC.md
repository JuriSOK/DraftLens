# DraftLens — Modeling Specification

**Status:** Approved specification — **no model has been trained and no algorithm is selected.**
**Version:** 1.0 · 2026-08-08

This document is the authoritative methodology specification for DraftLens. It operates inside [PRODUCT.md](PRODUCT.md) (product behaviour), [MVP.md](MVP.md) (scope), and [DATA.md](DATA.md) (what data actually exists). Where it is silent, those documents govern.

**What this document does:** fixes the analytical structure, the population, the windows, the leakage rules, the validation protocol, and the evaluation criteria.
**What it deliberately does not do:** choose algorithms, features, weights, formulas, thresholds, or metrics. Those are empirical questions listed in §28 and must be resolved by experiment, not assumption (DEC-017, PRODUCT.md §20 "Honest evaluation").

---

## 1. Purpose

To specify how DraftLens turns verified pre-draft data into rankings, scores, profile fits, and comparables — and how each of those is validated without leaking post-draft information.

Three principles constrain everything below:

1. **Temporal honesty.** No information that postdates the draft being evaluated may influence any output for that draft, including through feature construction, normalisation constants, imputation fits, hyperparameter choice, or population membership.
2. **Explainability over performance.** A methodology that cannot support per-prospect, per-dimension explanation is at a disadvantage regardless of its metrics (PRODUCT.md §16).
3. **No invented numbers.** Every displayed score traces to documented metrics computed from raw statistics (DEC-018). Scores that exist only for visual appeal are prohibited.

---

## 2. Analytical systems — four, kept independent

| System | Question | Nature |
| --- | --- | --- |
| **A. General Draft Board** | How strong is this prospect's overall draft outlook? | Supervised, historically validated |
| **B. Team Need scoring** | How well does this prospect match the traits the user cares about? | Deterministic multi-criteria ranking — **not a predictive model** |
| **C. Sub-scores / archetypes** | How does this prospect rate on Shooting, Playmaking, …? | Transparent statistical composites |
| **D. NBA comparables** | Which NBA players' statistical style most resembles this prospect? | Unsupervised similarity |

**No single model may solve more than one of these.** In particular, Team Need must not reuse the General Draft Board's predictive output (DEC-006, DEC-053), and the comparables engine must never read board features or targets (DATA.md §10.1).

---

## 3. Historical population — early entrants only

### 3.1 The approved population

> **The primary General Draft Board historical population is FINAL NCAA EARLY ENTRANTS ONLY**, for each draft year. It contains both drafted and undrafted early entrants.

The historical question is therefore:

> *"Among NCAA players who officially declared as final early entrants, which prospects were selected in the NBA Draft, and how highly were the selected players chosen?"*

### 3.2 Why the previous union population was rejected

[DATA.md](DATA.md) §24.5 measured the defect directly: under the earlier rule (early entrants ∪ drafted NCAA players), **212 of 212 non-early-entrants were drafted — 100.0%** across 2011–2026, and all 469 undrafted players were early entrants.

A senior or automatically-eligible player could only enter that population *because we already knew they were drafted*. **Population membership itself carried post-draft information.** No feature engineering could remove it, because the leak was in the sampling frame rather than in any column.

Restricting to declared early entrants eliminates it: the declaration list is published before the draft (final list ~8 days prior — DATA.md §2), so membership is genuinely pre-draft information.

### 3.3 Seniors and automatically-eligible players

They **remain in the raw data** (`data/raw/draft_population/`) for descriptive analysis, prospect display, and the reconstructed-population documentation. They are **excluded from the primary ML training and backtesting dataset** and must never be silently mixed into the positive or negative class.

This may be reconsidered **only** if a defensible *pre-draft* population of automatically-eligible players is obtained. DATA.md §3.1 established that no name-level list exists for any year, so this is not expected.

### 3.4 Consequence — the honest scope claim

The board ranks **declared early entrants**, not every draft-eligible NCAA player. Every product surface that describes the board's coverage must say so. This is narrower than [PRODUCT.md](PRODUCT.md) §14's current wording — see §29.

### 3.5 Verified population sizes

Descriptive counts from the acquired data (no features computed):

| Draft year | Early entrants | Drafted | Undrafted | Drafted % |
| --- | --: | --: | --: | --: |
| 2011 | 39 | 27 | 12 | 69.2 |
| 2012 | 43 | 30 | 13 | 69.8 |
| 2013 | 43 | 28 | 15 | 65.1 |
| **2014** | 41 | 28 | 13 | 68.3 |
| 2015 | 44 | 27 | 17 | 61.4 |
| 2016 | 52 | 27 | 25 | 51.9 |
| 2017 | 61 | 37 | 24 | 60.7 |
| 2018 | 72 | 39 | 33 | 54.2 |
| 2019 | 76 | 40 | 36 | 52.6 |
| 2020 | 65 | 40 | 25 | 61.5 |
| **2021** | **188** | 50 | **138** | **26.6** |
| 2022 | 132 | 43 | 89 | 32.6 |
| 2023 | 79 | 41 | 38 | 51.9 |
| 2024 | 49 | 33 | 16 | 67.3 |
| **2025** | 28 | 26 | **2** | **92.9** |
| **2026** *(holdout)* | **26** | 25 | **1** | **96.2** |

| Window | n | Drafted | Undrafted | Drafted % |
| --- | --: | --: | --: | --: |
| **Main development 2014–2025** | **887** | 431 | 456 | **48.6** |
| Secondary robustness 2011–2013 | 125 | 85 | 40 | 68.0 |
| **Final holdout 2026** | **26** | 25 | 1 | **96.2** |

The main window is **nearly class-balanced overall (48.6%)** — a substantial improvement over the union population — but see §4.3 and §12.1 for the two problems these numbers reveal.

---

## 4. ML windows

### 4.1 Approved windows

| Window | Years | Role |
| --- | --- | --- |
| **Main development** | **2014–2025** | Training, temporal validation, feature/model/hyperparameter selection |
| **Final holdout** | **2026** | One evaluation only, after the methodology is frozen |
| Secondary robustness | 2011–2013 | Sensitivity analysis only — never in the default training set |

**Why 2014:** DATA.md §24.3 verified a coverage regime change — hoopR/ESPN core rows jump 5,740 → 10,587 and teams 542 → 628 between 2013 and 2014. Per-season normalisation baselines computed across that break are not comparable. Drafted counts in 2011–2013 are normal, so those years remain usable for robustness checks; they are not the default.

### 4.2 Expanding-window folds — verified sizes

| Fold | Train years | Train n | Validate | Validate n | Val. undrafted |
| --- | --- | --: | --- | --: | --: |
| 1 | 2014–2018 | 270 | 2019 | 76 | 36 |
| 2 | 2014–2019 | 346 | 2020 | 65 | 25 |
| 3 | 2014–2020 | 411 | 2021 | 188 | 138 |
| 4 | 2014–2021 | 599 | 2022 | 132 | 89 |
| 5 | 2014–2022 | 731 | 2023 | 79 | 38 |
| 6 | 2014–2023 | 810 | 2024 | 49 | 16 |
| 7 | 2014–2024 | 859 | 2025 | 28 | **2** |

Seven folds; training sets from 270 to 859 prospects. **Folds are not interchangeable** — fold 3 validates on 188 prospects and fold 7 on 28.

### 4.3 🔴 Two structural problems these numbers create

**(a) The 2025 fold is near-degenerate.** Two undrafted prospects. ROC-AUC, PR-AUC, and every calibration metric are effectively undefined at that sample size — a single misordering swings AUC by a large fraction. **Fold 7 must not be treated as equal evidence to folds 1–5**, and no model may be selected on its result. The specification requires reporting per-fold metrics with fold sizes attached, never a bare mean across folds (§12.3).

**(b) The holdout base rate differs sharply from the training window.** Training is 48.6% drafted; the 2026 holdout is **96.2% drafted** (25 of 26). This is not noise — declared early entrants collapsed from 188 (2021) to 26 (2026), so only serious prospects now declare. It is a genuine population regime shift, plausibly driven by NIL and transfer-portal economics reducing speculative declarations.

**Consequence:** a Stage A model calibrated on a 48.6% base rate will be **badly miscalibrated** on 2026. The 2026 holdout therefore tests **ranking quality, not probability calibration**, and the evaluation must say so rather than reporting a Brier score as if it were comparable.

**Formalised as DEC-066.** With 25 of 26 holdout prospects drafted, ROC-AUC, PR-AUC and calibration on 2026 are statistically uninformative or unstable. **Historical expanding-window folds are the primary evidence for Stage A.** 2026 is the final board/replay showcase; any Stage A metric computed on it after the freeze must carry an explicit instability warning. The population must never be expanded to improve its class balance. Recency weighting or a recent-years-only sensitivity variant should be tested (§11.4), but selection must still happen without touching 2026.

### 4.4 COVID cohort

2021 (188 early entrants, 26.6% drafted) and 2022 (132, 32.6%) are the COVID eligibility cohorts. Together they are **320 of 887 rows — 36% of the main window** — so pooled training is disproportionately shaped by them.

**They must not be automatically removed.** Required sensitivity analyses (§11.4): (A) all years; (B) 2021–2022 excluded; (C) 2021–2022 down-weighted. Any exclusion must be justified by measured stability differences, not by intuition.

---

## 5. Target definitions

### 5.1 Stage A — drafted vs undrafted

- **Population:** all final NCAA early entrants in the training years.
- **Target:** `drafted ∈ {0, 1}`.
- **Source:** `data/raw/draft_targets/` exclusively.

### 5.2 Stage B — draft position among drafted players

- **Population:** early entrants who were **actually drafted** (431 in the main window; 26–50 per year).
- **Target:** to be selected from the four candidates in §6.3.

### 5.3 Target hygiene

Targets are read only from `data/raw/draft_targets/` and are never joined into a feature frame before the feature-generation boundary (DATA.md §24.8). **Targets are never normalised** — normalisation applies to features only (§9.3).

---

## 6. General Draft Board architecture

### 6.1 Two-stage design — the primary methodology to evaluate

```
                    PROSPECT (declared early entrant)
                              │
                    pre-draft feature vector
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
        STAGE A                          STAGE B
   P(drafted)                     expected draft position
   calibrated probability          | drafted (conditional)
              │                               │
              └───────────────┬───────────────┘
                              ▼
                   GENERAL DRAFT SCORE  (§17)
                              ▼
                      RANKED BOARD /100
```

DraftLens is a **ranking and decision-support product**, not a pick predictor (PRODUCT.md §4). The two-stage split exists because "will this player be drafted at all?" and "how high will a drafted player go?" are different questions with different populations, and collapsing them into one regression would force the model to explain undrafted players with a fabricated pick number.

### 6.2 Why not a single model

A single regression over all early entrants must assign undrafted players some sentinel position (61, 100, NaN), which invents data (DEC-017) and distorts the loss surface. A single classifier over draft tiers with an "undrafted" tier is a legitimate **alternative** worth testing (§6.4), but the two-stage design is the primary structure to evaluate.

### 6.3 Stage B target candidates — to be compared empirically

| # | Candidate | Strengths | Weaknesses |
| --- | --- | --- | --- |
| **A** | Exact pick as regression target | Simple, directly interpretable | Treats pick 1→2 as equal to 59→60, which is basketball-nonsense; heteroscedastic |
| **B** | Transformed pick (e.g. log or reciprocal) | Compresses the tail so top-pick errors dominate appropriately | Transformation choice is itself a free parameter needing justification |
| **C** | Ordinal draft tier | Robust to pick-level noise; interpretable; matches how scouts speak | Loses within-tier ordering; boundaries risk being arbitrary; **sparse cells** — see below |
| **D** | Learning-to-rank | Directly optimises what the product outputs | More complex; harder to explain; smaller literature at this sample size |

**All four must be tested. None is approved.**

**Verified tier-sparsity constraint.** If tiers are tested, the intuitive boundaries (Lottery 1–14, Rest of R1 15–30, Early second 31–45, Late second 46–60) produce **thin cells**: late-second counts per year range from **0 (2012) to 12 (2021)**, and 2025–2026 have 1–2. These boundaries are a **candidate interpretable representation only** and must not be hard-coded because they feel natural. Any tiering must report per-tier counts per year and justify boundaries against observed density.

### 6.4 Alternative single-stage design (secondary)

A multi-class ordinal model over {undrafted, late second, early second, rest of R1, lottery} is a legitimate secondary structure worth one comparison. It naturally handles undrafted players without a sentinel. It is not the primary design because it fuses two questions with different populations and makes calibrated draft probability harder to expose.

---

## 7. Feature families — candidates only

Derived exclusively from data verified in [DATA.md](DATA.md) §22 and §24. **Availability is not a reason for inclusion.** The final set must be selected on validity, stability, missingness, and temporal-validation evidence.

| Family | Candidate features | Source | Status |
| --- | --- | --- | --- |
| **Identity / context** | position (100% fill, all seasons); season; conference / team context if justified | `player_core`, `player_box` | Strong |
| **Playing time / role** | games, starts, minutes, minutes per game | `player_box` (`starter`, `did_not_play`) | Strong |
| **Scoring** | points, FGM/FGA, 2P (= FG − 3P), 3PM/3PA, FTM/FTA, scoring rate | `player_box` | Strong |
| **Shooting efficiency** | FG%, 2P%, 3P%, FT%, eFG%, TS% | Derived from `player_box` | Strong |
| **Volume / diet** | FGA rate, 3PA rate, FT rate (FTA/FGA) | Derived | Strong |
| **Playmaking** | assists, turnovers, AST/TO, AST%, TOV% | `player_box` + team aggregates | Strong |
| **Rebounding** | OREB, DREB, REB, ORB%, DRB%, TRB% | `player_box` + team + opponent | Strong |
| **Defense (box proxies)** | steals, blocks, STL%, BLK%, fouls | `player_box` | **Limited — see §18.3** |
| **Role / possession** | usage%, per-40, per-100-possession | Derived (team totals from `player_box`) | Strong |
| **Shot style** | dunk / layup / tip / jumper frequency, rim-attempt share, rim FG%, 3PA share, assisted-shot rate, unassisted rim finishing | `shots` (`type_text`, `athlete_id_2`) | Strong |
| **Physical** | height (76.7–99.2% fill), weight (57.1–94.7% fill) | `player_core` | Moderate — coverage varies by season |

**Team and opponent totals are derivable from `player_box` alone** — DATA.md §22.2 verified 99.89% points reconciliation and a 100% opponent self-join, so `team_box` is not required for rate statistics.

**Two verified data hazards that constrain feature construction:**
- `shots` contains **only made free throws** — FT metrics must come from `player_box`, never `shots` (DATA.md §22.3).
- `shots` coordinates are contaminated with ±2.1×10⁸ int32 sentinels. **Shot-style features should be built from `type_text`, not coordinates**, unless the usable-coordinate rate is measured first.

---

## 8. Prohibited features and leakage rules

### 8.1 Absolutely prohibited as General Draft Board inputs

Draft pick · round · drafted flag · drafting team · NBA career statistics · NBA rookie statistics · current NBA team · current NBA experience · future-season NCAA data · analyst rankings · mock drafts · consensus boards · green-room invitations · **`early_entrant`** · **`population_source`** · current age · **DOB missingness indicator** · any feature derived from post-draft outcomes.

Note that within the early-entrant-only population `early_entrant` is constant, so it is trivially uninformative as well as prohibited; `population_source` remains prohibited because it encodes how a record entered the frame.

### 8.2 Age / date of birth — excluded, with the reasoning recorded

**DOB and derived age are not approved as General Draft Board historical model features.** Also prohibited: missing-DOB indicators, sentinels exposing missingness, and imputation intended to reintroduce the feature.

The evidence (DATA.md §23.4, §24.7):
- Drafted sample DOB coverage **100%**; undrafted sample **69%**. Every missing historical DOB in the audit belonged to an undrafted prospect.
- Fill declines monotonically from **71.9% (2011) to 1.6% (2026)**, consistent with ESPN backfilling birth dates for players who turned professional.

**Availability is therefore a function of the outcome.** Missingness is a leakage channel, not merely a gap.

**Approved uses:** prospect display, the 2026 profile (100% coverage via Wikidata), exploratory analysis, and a future controlled ablation. This fulfils PRODUCT.md §11's requirement that age be evaluated empirically — it was evaluated and excluded on leakage grounds, not dropped from the product.

### 8.3 The leakage audit is a required phase

Phase ML-1 (§27) must re-derive the leakage table for the actual feature set. Any feature whose *availability* correlates with the target is suspect regardless of its values.

---

## 9. Position and season normalisation

### 9.1 Position

DraftLens uses PG / SG / SF / PF / C (DEC-009). Position is 100% populated in every acquired season.

Rebounding, height, and blocks mean different things by position (PRODUCT.md §8). Candidate approaches — **to be validated, none approved**: within-position percentiles · within-position z-scores · position as a categorical feature · model interaction terms · hybrid (position-relative for physical/rebounding, raw for efficiency).

Open issues: small position samples in some year × position cells; disagreement between sources on position labels; whether the same normalisation should serve both the board and Team Need (§19).

### 9.2 Season

The NCAA environment changes across the window, and DATA.md documented three specific shifts: the 2014 coverage break, 2021 COVID anomalies, and unstable class balance.

Candidates: z-scores within season · percentiles within season · robust ranks · season × position cells.

**Critical constraint:** normalisation statistics must be fit **only on data available before the evaluated draft**. Fitting a scaler on the full 2014–2025 pool and applying it to a 2019 validation fold leaks future information into the 2019 prediction. Every normalisation must be re-fit inside each fold.

### 9.3 Targets are never normalised

Normalisation applies to features. Draft position is the target and is transformed only as an explicit Stage B target-design choice (§6.3), which is a different decision from feature scaling.

---

## 10. Missing data

### 10.1 Three kinds, handled differently

| Type | Example | Character |
| --- | --- | --- |
| **Structural** | Combine test not taken; player attempted no shots | Informative absence — the player was never in a position to record it |
| **Source** | Weight unrecorded in a given season (57.1% fill in 2025) | Closer to missing-at-random, but varies systematically by season |
| **Biographical** | Date of birth | **Outcome-correlated — see §8.2** |

### 10.2 Candidate strategies — none approved

Model-native missing handling · median or position-aware imputation · missing indicators **only where they cannot leak** · feature exclusion where coverage is too poor.

### 10.3 Required rule

> **A missingness indicator is itself a feature and must undergo the same leakage review as any other.**

DOB demonstrates why: the indicator would have been the most target-predictive column in the dataset while carrying no basketball information at all.

### 10.4 Entity-match failure is not missing data

DATA.md §12.1 type 4: a failed join looks like missingness but is a pipeline defect, and DATA.md §9.2 showed such failures concentrate in the undrafted class. Match failures must be counted and reported separately, never imputed.

---

## 11. Temporal validation

### 11.1 Random splitting is prohibited

Random train/test splitting is **prohibited for final model evaluation** (DEC-012). It would place same-class teammates and same-year prospects on both sides of the split and destroy the temporal guarantee.

### 11.2 Protocol

Expanding-window folds as specified in §4.2: train 2014→N, validate N+1, roll forward. Everything fit inside a fold — imputation, scalers, percentile baselines, feature selection, hyperparameters, calibration — must be fit on training years only.

### 11.3 Fold weighting

Per-fold metrics are reported **with fold sizes attached**. A bare mean across folds is prohibited: it would weight the 27-prospect 2025 fold equally with the 169-prospect 2021 fold. Whether to weight by fold size, report medians, or report the full distribution is an open question (§28).

### 11.4 Required sensitivity analyses

1. **COVID:** all years vs. 2021–2022 excluded vs. down-weighted.
2. **Window start:** 2014–2025 (default) vs. 2011–2025 (tests whether the coverage break matters in practice).
3. **Recency:** uniform weighting vs. recency weighting, motivated by the §4.3(b) base-rate shift.
4. **Fold stability:** does the selected model's ranking quality hold across folds, or is it carried by one or two?

---

## 12. Stage A evaluation

### 12.1 Metric requirements

**Accuracy alone is prohibited.** At an 88.5% base rate (2026), predicting "drafted" for everyone scores 88.5% accuracy while being useless.

| Role | Candidates |
| --- | --- |
| Primary (threshold-independent) | ROC-AUC, PR-AUC |
| Probabilistic quality | log loss, Brier score |
| Supporting (threshold-dependent) | precision, recall, F1 — always with the threshold stated |
| Calibration | reliability curves, calibration error |

**The final primary metric is TBD** and must be chosen after examining per-fold class balance. PR-AUC is likely preferable where the undrafted class is small, but this must be decided on evidence.

### 12.2 Calibration matters — and will not transfer to 2026

DraftLens intends to expose probability-like outputs, so calibration must be evaluated. But §4.3(b) means a model calibrated at a 48.6% base rate faces an 88.5% base rate in 2026. **Calibration metrics on the 2026 holdout must be reported as expected-to-degrade and must not be used to judge the methodology.** The 2026 holdout tests ranking.

### 12.3 Degenerate folds

The 2025 fold has **2 undrafted prospects**. Report its metrics, flag them as unstable, and **do not select any model on them**.

---

## 13. Stage B evaluation

Population: drafted early entrants (26–50 per year).

| Role | Candidates |
| --- | --- |
| **Rank quality (weighted heavily)** | Spearman ρ, Kendall τ, NDCG |
| Magnitude error | MAE on pick, RMSE on pick |
| Ordinal (if tiers tested) | tier accuracy, adjacent-tier accuracy, quadratic-weighted κ |

**Rank-quality metrics receive substantial weight** because the product outputs a ranking, not a pick prediction. MAE in picks is reported for interpretability but must not be the sole selection criterion — a model can achieve good MAE while ordering the top of the board badly, which is precisely the region that matters.

No single metric is approved.

---

## 14. Board-level evaluation

Stage A and Stage B metrics do not tell you whether **the board** is good. The combined ranking must be evaluated directly.

Questions the evaluation must answer:
- Are actually-drafted players concentrated near the top?
- How many actual first-round picks appear in the model's top 30?
- How many actual lottery picks appear in the model's top 14?
- How strongly does board order correlate with actual draft order among drafted prospects?
- Is ranking quality stable across years, or carried by a few?

Candidate metrics: **Precision@K, Recall@K, NDCG@K** (K ∈ {5, 14, 30}), and **Spearman correlation among drafted prospects**.

**Caveat on K:** with only 26–28 prospects in recent classes, K = 30 exceeds the population. K values must be chosen relative to each year's population size, and this must be stated rather than silently truncated.

**Never optimise against the 2026 holdout** (§25).

---

## 15. Baselines

Complex models must beat simple ones on temporal validation before being considered.

Required baselines: **(1)** scoring average only; **(2)** a simple standardised box-score composite; **(3)** logistic regression on a small interpretable feature set; **(4)** a position-aware percentile composite; **(5)** naive average historical pick by position / statistical profile.

**Prohibited as baselines in the predictive pipeline:** public mock drafts, analyst consensus boards (DEC-013). They may later be shown as **external comparison benchmarks** if legally and practically available, but they must never inform model selection.

---

## 16. Candidate model families

**No algorithm is approved.** Dataset size is modest — 887 prospects in the main window, 431 for Stage B.

| Stage | Interpretable baseline | Nonlinear candidates |
| --- | --- | --- |
| **A** | Logistic regression (regularised) | Random forest · gradient-boosted trees · HistGradientBoosting · XGBoost / LightGBM only if later justified |
| **B** | Linear / regularised regression | Tree-based regression · gradient boosting regression · ordinal classification · ranking-oriented approaches |

**Complexity principle.** DraftLens prioritises temporal generalisation, explainability, calibration, and robustness over leaderboard performance. Prefer the simpler model unless a more complex one delivers **consistent** improvement across folds — not an improvement carried by one fold.

**Deep learning is not justified** for this tabular problem at this sample size. Hundreds to low thousands of rows with dozens of correlated features is the regime where regularised linear models and small tree ensembles typically win, and where neural networks overfit.

---

## 17. Overall Score principles

The board must produce an **Overall Score out of 100** (PRODUCT.md §9). It must not be hand-invented.

### 17.1 Candidate constructions — to be evaluated

1. Monotonic transformation of a single validated model output.
2. Calibrated `P(drafted)` combined with the conditional draft-position signal.
3. Percentile rank of the combined signal within the draft class.
4. Another documented reproducible transformation.

### 17.2 Requirements — binding

- **Order-preserving:** the score must preserve the analytical ranking exactly. If A ranks above B, A's score must be ≥ B's.
- **Reproducible:** same inputs → same score, deterministically.
- **Interpretable:** the transformation must be explainable in one or two sentences to a scout.
- **No false precision:** a score must not imply a literal percentage unless it *is* a calibrated probability. If it is not, the product must not present it as one.
- **No visual-only rating:** every point of the scale traces to a validated output.
- **Class-relative or absolute must be stated.** A percentile within class is not comparable across years; an absolute scale is. Whichever is chosen must be labelled in the UI.

Coefficients and the final transformation are TBD.

---

## 18. Sub-scores

### 18.1 Families and data support

| Sub-score | Data support | Status |
| --- | --- | --- |
| **Shooting** | 3P/2P/FT splits, eFG%, TS%, shot-type mix, assisted rate | 🟢 Strong |
| **Playmaking** | assists, AST%, AST/TO, TOV%, shot-level assist linkage | 🟢 Strong |
| **Rebounding** | OREB/DREB/REB, ORB%/DRB%/TRB% with opponent context | 🟢 Strong |
| **Size / Physical** | position (100%), height (76.7–99.2%), weight (57.1–94.7%) | 🟢 Strong |
| **Defense** | steals, blocks, STL%, BLK%, DREB%, fouls | 🟡 **Box-score proxies only** |
| **Athleticism** | — | 🔴 **Not available without Combine** |

### 18.2 🔴 Athleticism must not be faked

There is **no athleticism measurement** in the acquired data. Dunk frequency is a *style* signal confounded by position, role, and team system — it is not a vertical leap.

> **An Athleticism sub-score must not be manufactured from unrelated box-score statistics.** In the MVP without Combine data, Athleticism is **unavailable or incomplete** and must be shown as such — omitted, or displayed as explicitly missing (DEC-016 requires missing data to be disclosed, not hidden).

### 18.3 Defense must be labelled honestly

The Defense sub-score measures **box-score defensive production**, not defensive quality. There is no matchup data, no opponent shooting-when-defended, no on/off context, and no deterrence measure. Steals and blocks are noisy and position-confounded.

It must be **named and described** as box-score defensive production wherever it appears. Calling a player an "elite defender" from these inputs is prohibited (§22).

### 18.4 Construction

Sub-scores are transparent composites of normalised factual metrics, not model outputs. Formulas, inputs, and weights are TBD and must be justified by basketball logic plus sensitivity analysis. Every sub-score must expose its inputs (DEC-018).

---

## 19. Team Need mode

### 19.1 Not a predictive model

Team Need is a **deterministic multi-criteria ranking** reflecting user preference. It does **not** reuse the General Draft Board's predictive output.

> The General Draft Board asks *"how strong is this prospect overall?"*
> Team Need asks *"how well does this prospect match the traits I care about?"*

These are not blended by default (DEC-006, PRODUCT.md §7). Team Need does not include Overall Score unless a later explicit product decision adds it.

### 19.2 Custom criteria

Simple-mode dimensions: Shooting, Playmaking, Defense, Rebounding, Size, and Athleticism **only if available** (§18.2).

Candidate design: `normalized_dimension_score × user_weight`, aggregated and rescaled to a Fit Score. **The exact transformation is TBD**, including how weights are normalised, whether dimensions are percentile or z-scored, and how missing dimensions are handled without penalising or rewarding absence.

### 19.3 Requirements

Weights visible · dimensions inspectable · raw supporting statistics visible · fully deterministic · no generative AI · **user weights are preferences, not learned coefficients** and must never be fitted to data.

---

## 20. The six MVP player profiles

Candidate factual dimensions per profile. **No weights are assigned.** Feasibility ratings from DATA.md §22.5.

**1. Shooter — 🟢 GREEN**
3P% · 3PA rate · 3PA volume · FT% · eFG% · TS% · jump-shot share · **unassisted three-point rate** (self-creation vs. spot-up)

**2. Slasher / Rim Attacker — 🟢 GREEN**
Rim-attempt share (layup + dunk + tip / FGA) · rim FG% · free-throw rate (FTA/FGA) · **unassisted rim share** · dunk frequency

**3. Playmaker — 🟢 GREEN**
AST% · AST/TO · TOV% · assists per possession · usage% · shot-level assist decomposition by shot type created

**4. 3&D Wing — 🟡 YELLOW**
Shooting half as profile 1 · STL% · BLK% · DREB% · height / positional size
> ⚠️ **Defense is approximated by box-score proxies only.** No point-of-attack, matchup, or opponent-shooting data exists. This limitation must be shown in the product wherever the profile appears.

**5. Rim Protector — 🟡 YELLOW**
BLK% · defensive rebounding · height · weight · positional context
> ⚠️ **Deterrence and opponent rim FG% are unavailable.** Blocks reward one visible action and miss most of rim protection. This limitation must be shown in the product.

**6. Stretch Big — 🟢 GREEN**
Big position (PF/C) · 3P% · 3PA rate · FT% · rebounding · positional size

**MVP constraint:** exactly **one** predefined profile at a time (DEC-028). Combinations are out of scope.

Final weighting must be justified through transparent basketball logic and sensitivity analysis — never fitted to draft outcomes, which would silently turn Team Need into a second draft-board model.

---

## 21. NBA statistical comparables

### 21.1 Structure

A **separate unsupervised similarity system**. Exactly **three** comparables per prospect (DEC-014).

- **Input:** the prospect's current NCAA statistical / style profile.
- **Reference:** actual NBA player-season profiles from `hoopr_nba/player_season_stats` (8,342 player-seasons, 2011–2026, 40 stat dimensions, no schema drift).

### 21.2 The normalisation requirement

Raw NCAA and raw NBA values must **never** be compared directly (DEC-015). 19 PPG in the NCAA is not 19 PPG in the NBA.

> The comparison is **relative statistical style to relative statistical style**, not absolute production to absolute production.

Candidate representations to evaluate: within-league percentiles · within-position percentiles · z-scores · per-possession normalisation · role/style dimension vectors · composite dimension scores.

**Competition level is not claimed to be equivalent.** The product must state that similarity is descriptive style resemblance and does **not** predict a similar NBA career (PRODUCT.md §13).

### 21.3 NBA reference-season representation — unresolved

| Candidate | Trade-off |
| --- | --- |
| A. Latest season | Current and recognisable; volatile; penalises injured or aging players |
| B. Multi-season average | Stable; blurs role changes; mixes distinct career phases |
| **C. Recent 2–3 season average** | Balances stability and currency | 
| D. Peak season | Flattering and memorable; systematically unrepresentative |
| E. Role-stabilised season | Most principled; requires defining "stable role", adding a free parameter |

**For later empirical testing, a recent multi-season representation likely offers better stability than a single season. This is a hypothesis, not an approval.** The choice must be tested against whether comparables remain stable under small input perturbations.

### 21.4 Similarity metric — unresolved

Candidates: cosine similarity · Euclidean distance on standardised features · Manhattan distance · nearest neighbours.

Requirements: interpretable · stable · **robust to correlated features** (basketball statistics are heavily collinear, which distorts naive Euclidean distance) · explainable in the product.

**Deep embeddings are prohibited** — they would make the comparable inexplicable, violating PRODUCT.md §16.

### 21.5 Firewall

The comparables engine reads `nba_comparable_profiles` and the prospect's NCAA profile. It **never** reads draft targets, and it is never joined to board training data on `canonical_player_id` (DATA.md §10.1). The only place board output and comparables meet is the rendered prospect page, after both are computed independently.

---

## 22. Explainability

### 22.1 General Draft Board

Must eventually expose: strongest positive factors · strongest negative factors · the relevant raw statistics · position context.

Candidate techniques, dependent on the final model: for linear models, coefficient × standardised feature contribution; for tree models, feature importance or SHAP **if justified**. **SHAP is not required** if the selected model does not need it — a regularised linear model explains itself more clearly and more cheaply.

### 22.2 Team Need

Simpler and fully deterministic: explanations derive directly from dimension scores and user weights.

```
Why Prospect A over Prospect B?
+ stronger three-point volume
+ higher defensive score for position
+ greater wingspan
- Prospect B provides stronger playmaking
```

**No LLM or generative AI is required anywhere** (DEC-019).

### 22.3 Strengths and weaknesses

Must be derived statistically, never asserted. Candidate approach: identify dimensions at high or low percentiles relative to the same draft class, the same position, or a historical position distribution.

```
+ 91st percentile 3PA rate among SGs
+ 86th percentile AST%
- 24th percentile defensive rebounding
```

**Prohibited:** calling a player an "elite defender" from box-score proxies alone (§18.3). Claim strength must match evidence strength.

---

## 23. Data coverage

Prospect pages need a Data Coverage indicator (MVP.md §12). The formula is **TBD**.

Two binding constraints:

1. It must reflect availability of expected fields, computed from an explicit field manifest with declared essential / desirable / optional tiers (DATA.md §12).
2. **It must never feed the predictive model.** A prospect must not rank higher because more data happens to exist about them — which, given §8.2's finding that availability correlates with outcome, is exactly the failure mode to guard against.

---

## 24. Combine policy

Combine data is **optional enrichment** and was not acquired (DEC-046). **The General Draft Board must operate without it**, and MVP viability does not depend on it.

If added later: measurements may enrich Size and enable Athleticism · **missing Combine participation must never exclude a prospect** (DEC-016) · **Combine presence must itself be leakage-reviewed** · the pre-2024 vs 2024+ mandatory-participation regime change (DATA.md §8.3) must be handled explicitly, since presence means different things on either side of it.

---

## 25. 2026 final holdout policy — non-negotiable

**Holdout population: the 26 final 2026 NCAA early entrants.** Seniors are not added merely because we now know they were drafted.

**2026 may be inspected for:** raw-data readiness · schema validation · identity matching · application demo wiring.

**2026 outcomes must NOT be used for:** feature selection · model selection · hyperparameter selection · threshold selection · calibration choice · score-transformation choice · profile-weight tuning.

**Protocol:** once the methodology is frozen (Phase ML-7), run **exactly one** final 2026 evaluation.

> **If the result is poor, report it honestly and do not tune against it afterward.**

This follows directly from PRODUCT.md §20 ("Honest evaluation"). Note §4.3(b): the 2026 base rate (88.5%) differs sharply from training (48.6%), so degraded calibration is *expected* and is not evidence of a broken methodology — ranking metrics are the meaningful test.

---

## 26. Reproducibility

All ML experiments must be **Python-based** (DEC-033, DEC-037), seeded wherever randomness exists, configuration-driven where reasonable, and temporally reproducible.

Every experiment records: data window · feature set · target · preprocessing · model · parameters · validation folds · metrics (per fold, with fold sizes) · random seed · timestamp.

**Do not build an experiment-tracking platform.** A structured experiment report — one file per experiment — is sufficient and is what the hackathon deliverable needs.

---

## 27. Implementation sequence

**None of these phases is executed by this document.**

| Phase | Work | Gate |
| --- | --- | --- |
| **ML-0** | Build the model-ready dataset from **early entrants only** | Population counts match §3.5 exactly *(done; counts corrected in ML-0.1 — see [ML0_REPORT.md](ML0_REPORT.md))* |
| **ML-1** | EDA and leakage audit on the actual feature set | Leakage table re-derived; availability-correlation checked per feature |
| **ML-2** | Derive transparent statistical features (§7) | Every feature traces to documented source columns |
| **ML-3** | Establish baselines (§15) | All five baselines measured on the fold protocol |
| **ML-4** | Train Stage A candidates | Beats baselines consistently across folds |
| **ML-5** | Train Stage B candidates; compare the four target designs | Rank metrics reported per fold |
| **ML-6** | Construct and validate the Overall Board ranking | Board metrics (§14) computed; §17 requirements satisfied |
| **ML-7** | **Freeze** the General Draft methodology | Written frozen spec; no further tuning permitted |
| **ML-8** | Run the 2026 holdout **once** | Single evaluation; result reported as-is |
| **ML-9** | Build Team Need scoring | Deterministic; no fitting to draft outcomes |
| **ML-10** | Build the NBA similarity system | Comparables stable under perturbation |

Phases ML-9 and ML-10 are independent of ML-4…ML-8 and may proceed in parallel — they are separate analytical systems (§2).

---

## 28. Open questions — none may be resolved by assumption

**Stage A:** primary metric · model family · calibration method · threshold policy (if any) · fold weighting or aggregation rule.

**Stage B:** regression vs. transformed regression vs. ordinal vs. ranking · tier boundaries if tiers are used · primary metric.

**Board:** exact Overall Score transformation · whether the score is class-relative or absolute · K values for Precision@K given small classes.

**Features:** final feature set · position-normalisation method · season-normalisation method · missing-value method · whether shot coordinates are usable at all.

**Population and window:** how to report a holdout with a single undrafted prospect · COVID-year treatment · whether 2011–2013 are included after sensitivity analysis · recency weighting.

**Team Need:** sub-score formulas · profile weights · Fit Score transformation · missing-dimension handling.

**Comparables:** NBA reference-season representation · similarity metric · shared representation space.

**Product:** data coverage formula · explainability method for the final model · whether Combine is eventually added · whether Athleticism ships at all.

---

## 29. Conflicts identified with existing documents

Flagged, **not silently resolved.** No product document was modified.

### 29.1 PRODUCT.md §14 — ground-truth wording (open since DATA.md §3.7)

Current wording: *"how well can pre-draft data explain or reproduce where prospects were selected?"* — implying all prospects.

Under §3.1 the accurate claim is narrower: *"among NCAA players who declared as final early entrants, which were selected and how highly."* The change is an improvement in honesty, but PRODUCT.md should be updated by the owner to match.

### 29.2 MVP.md §5 — "all prospects available in the selected draft dataset"

With the early-entrant-only population, the **2026 board contains 26 prospects** (down from 53 under the union rule). This satisfies the requirement literally — all prospects in the selected dataset are shown — but it is a materially smaller board than the MVP language suggests, and search/filter across five positions on 26 players is thin.

**This is an owner decision**, not a specification change. Options: accept the smaller, more defensible board; display non-early-entrant drafted players as clearly-labelled *unranked* context; or revisit population scope. **The third option would reintroduce the leak and is not recommended.**

### 29.3 DEC-039 — superseded

The union population rule is superseded by the early-entrant-only rule. Marked in [DECISIONS.md](DECISIONS.md); history preserved.

### 29.4 No conflict with DATA.md

DATA.md §24.5 documents the union population as *acquired raw data*. The ML population is a subset of it. Both are correct; the raw layer intentionally retains more than the model consumes.
