# ML-6 — General Draft Board and Overall Score

**Phase:** ML-6 · board combination and product score
**Scope:** historical development window **2014–2025 only**
**Status:** complete — board method and Overall Score frozen
**Reproduce:** `python scripts/experiments/ml6_board_selection.py` then `python scripts/experiments/validate_ml6_board.py`

> **2026 holdout firewall.** No 2026 target was loaded, no 2026 Stage A probability or Stage B signal was generated, no 2026 board or score was built, and no 2026 pick was inspected. No formula or scaling constant was chosen using 2026. Enforced by [`validate_ml6_board.py`](../../scripts/experiments/validate_ml6_board.py) check 3 and `tests/ml/test_board.py::TestHoldoutFirewall`.
>
> **Both stages remained frozen.** ML-6 combines Stage A and Stage B outputs. It did not retrain, retune or recalibrate either, and Stage B remains `STANDARD`, not `SEASON_RELATIVE`.

---

## 1. Executive summary

**Selected board:**

```
final_board_signal = P(drafted)  ×  draft_slot_utility(Stage B predicted pick)
Overall Score      = round(100 × within-class percentile of that signal)
```

**Does Stage B earn its place? Yes** — but the honest margin is modest, and the case rests on consistency rather than size.

Against the Stage A-only board, the selected combination improves **all three** headline measures, and it is the only candidate that does so consistently:

| | Stage A only | Selected board | Δ |
| --- | --- | --- | --- |
| Binary macro ROC-AUC | 0.6986 | **0.7123** | +0.0137 |
| Graded board NDCG | 0.8159 | **0.8283** | +0.0124 |
| Drafted-only Spearman | 0.2461 | **0.2781** | +0.0320 |
| Graded NDCG fold SD | 0.0869 | **0.0594** | −0.0275 (better) |
| Graded NDCG worst year | 0.6590 | **0.7281** | +0.0691 |

The largest gain is not in the headline averages — it is in **stability**. Stage A alone is the least stable board in the study (fold SD 0.0869, worst year 0.6590); every combination cuts that materially. A board that collapses to 0.659 in its worst class is a worse product than one that never falls below 0.728.

Three findings shaped the choice:

1. **Stage B alone is not a board.** It ranks drafted prospects better than Stage A (Spearman 0.2968 vs 0.2461) but is *worse* at the more basic job of separating drafted from undrafted (graded NDCG 0.8095 vs 0.8159, improving in only 2 of 7 folds). It was trained only among drafted players and does not model draft likelihood.
2. **The two stages are only moderately correlated** (pooled Spearman 0.509), which is why combining them helps at all.
3. **The apparent best method on raw averages was rejected.** `E_LEXICOGRAPHIC` posted the highest graded NDCG (0.8395) but improves binary AUC by only +0.0029 and depends on an unjustifiable band-width constant — see §6.

---

## 2. Frozen Stage A

Unchanged, and verified unchanged by validator check 1:

```
Logistic regression | SET_2_BOX_SHOT_PROFILE (25 features) | SEASON_RELATIVE
| train-fold median imputation | position_3 one-hot
| class_weight="balanced" | C=0.25 | uncalibrated
```

Trained on **all** early entrants of the training years. Anchors unmoved: macro ROC-AUC 0.6986, pooled 0.6953, Brier 0.2238, ECE 0.0590.

**Stage A is the only DraftLens output that is a probability.**

## 3. Frozen Stage B

Unchanged, including the R-1 correction:

```
Ridge(alpha=10) | RAW_PICK target | SET_2_BOX_SHOT_PROFILE | STANDARD
```

Trained on **drafted** early entrants only. Anchors unmoved: macro Spearman 0.2968, Kendall 0.2089, NDCG 0.9043, MAE 13.21.

> `STANDARD`, **not** `SEASON_RELATIVE`. The +0.0031 macro Spearman available from switching is far inside the fold SD of 0.124 and is not sufficient to reopen Stage B (DEC-095). ML-6 did not reopen it.

---

## 4. Historical out-of-fold construction

Seven expanding-window folds, the same as every prior phase. For each:

- **Stage A** trains on all early entrants of the training years, then scores every validation-year prospect → `stage_a_probability`.
- **Stage B** trains on the drafted subset of those same training years, then scores **every** validation-year prospect → `stage_b_raw_pick`.

**617 out-of-fold prospects** across 2019–2025 (273 drafted / 344 undrafted). Zero missing Stage A values, zero missing Stage B values, and no prospect dropped from any board.

Applying Stage B to a prospect who historically went undrafted is legitimate and means one specific thing:

> *"If this basketball profile were draftable, which part of the draft does it resemble?"*

It is **not** a claim the prospect will be drafted and **not** a pick assignment. The underlying target is untouched: every undrafted prospect keeps `drafted = 0` and `pick = NULL`. Validator check 6 fails if any undrafted row acquires a pick value or non-zero relevance.

---

## 5. Stage B all-prospect extrapolation audit

Stage B was fitted only on drafted players, so what it does off that population had to be measured before anything was built on it.

| Group | n | min | p05 | median | p95 | max | mean | below 1 | above draft size | missing |
| --- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| drafted | 273 | −5.14 | 15.17 | 27.10 | 37.62 | 51.26 | 26.68 | 1 | 0 | 0 |
| undrafted | 344 | 7.89 | 19.17 | 31.30 | 44.16 | 56.77 | 31.37 | 0 | 0 | 0 |
| all | 617 | −5.14 | 16.46 | 29.15 | 42.37 | 56.77 | 29.29 | 1 | 0 | 0 |

**The extrapolation is well behaved.** Only **1 of 617** predictions (0.16%) falls outside the legal slot range, and none exceeds the draft size. Undrafted prospects land in a plausible late-draft region rather than at absurd values.

Undrafted profiles are predicted **4.7 picks later** on average (31.4 vs 26.7) — a real but weak separation, consistent with Stage B carrying some draft-likelihood signal despite never being trained for it.

**This does not make the number product-safe.** ML-5 established exact-pick prediction is not display-safe (MAE 13.21, 21% within 5 picks), and ML-6 does not revisit that. Stage B is used here strictly as a **Draft Position Signal**.

---

## 6. Candidate board combinations

Six predeclared methods × three Stage B transforms. **No weight search** — the only numeric weight anywhere is the single 0.5/0.5 equal-weight reference point, included so the multiplicative rule can be compared against the obvious naive alternative.

| Config | binary macro AUC | pooled AUC | macro AP | graded NDCG | drafted ρ | drafted τ | P@K | graded SD | graded worst |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| E_LEXICOGRAPHIC \| HIST_EMP | 0.7016 | 0.6743 | 0.7243 | **0.8395** | 0.2729 | 0.1895 | 0.6785 | **0.0546** | 0.7420 |
| E_LEXICOGRAPHIC \| WITHIN_BOARD | 0.7015 | 0.6742 | 0.7241 | 0.8394 | 0.2723 | 0.1888 | 0.6785 | 0.0545 | 0.7419 |
| D_RANK_FUSION \| WITHIN_BOARD | 0.7234 | **0.6839** | **0.7254** | 0.8295 | 0.3173 | 0.2298 | 0.6782 | 0.0635 | **0.7421** |
| F_EQUAL_WEIGHT_SUM \| WITHIN_BOARD | 0.7205 | 0.6790 | 0.7224 | 0.8288 | 0.3121 | 0.2260 | 0.6724 | 0.0632 | 0.7396 |
| C_MULTIPLICATIVE \| WITHIN_BOARD | **0.7244** | 0.6802 | 0.7227 | 0.8285 | **0.3297** | **0.2340** | 0.6777 | 0.0648 | 0.7406 |
| **C_MULTIPLICATIVE \| DRAFT_SLOT_UTILITY** | **0.7123** | **0.6830** | **0.7237** | **0.8283** | **0.2781** | **0.1973** | **0.6846** | **0.0594** | **0.7281** |
| A_STAGE_A_ONLY | 0.6986 | 0.6715 | 0.7127 | 0.8159 | 0.2461 | 0.1647 | 0.6792 | 0.0869 | 0.6590 |
| B_STAGE_B_ONLY \| WITHIN_BOARD | 0.6911 | 0.6411 | 0.6824 | 0.8095 | 0.2968 | 0.2089 | 0.6452 | 0.0760 | 0.6855 |

**Every combination beats Stage A alone** on graded NDCG, stability and worst-year. **Stage B alone loses** to Stage A on the joint objective, confirming it must not become the board.

### Stage B transforms tested

| Transform | Formula | Uses target info | Note |
| --- | --- | --- | --- |
| `WITHIN_BOARD_PERCENTILE` | percentile of Stage B quality within the class | no | Class-relative; gives Stage B full spread in the product |
| **`DRAFT_SLOT_UTILITY`** | `clip(pick, 1, size)` → `(size+1−clip)/size` | no | Keeps absolute slot meaning; **selected** |
| `HISTORICAL_EMPIRICAL_PERCENTILE` | percentile against the fold's **training-year** prediction distribution | no | Only cross-class absolute scale; reference is in-sample, so mildly optimistic — disclosed |

Clipping in `DRAFT_SLOT_UTILITY` is **predeclared**, not fitted, and touches 1 of 617 rows.

---

## 7. Evaluation relevance definition

Chosen **before** any candidate was evaluated:

```
undrafted → 0
drafted   → (draft_size + 1 − pick) / draft_size
```

Pick 1 scores 1.0; the last pick scores 1/size; every undrafted prospect scores exactly 0. Normalising by that year's verified draft size means a late pick in a 58-pick draft is not penalised against a 60-pick draft.

**This is an EVALUATION quantity, not a target.** It never assigns a synthetic pick to an undrafted prospect, and Stage B is never trained on it. Linear in slot — no exponential "NBA value curve", because no external source justifies one here and curvature is not a free parameter to tune.

---

## 8. Fold-by-fold performance of the finalists

Graded NDCG (the joint objective):

| Year | A only | C \| UTILITY | C \| PCT | D fusion | E lexico |
| --- | --- | --- | --- | --- | --- |
| 2019 | 0.8391 | **0.8831** | 0.8985 | 0.8961 | 0.8747 |
| 2020 | 0.8078 | **0.8126** | 0.7659 | 0.7666 | 0.8263 |
| 2021 | 0.6590 | **0.7281** | 0.7406 | 0.7421 | 0.7419 |
| 2022 | 0.8021 | **0.8024** | 0.7971 | 0.7997 | 0.8012 |
| 2023 | 0.7824 | **0.8021** | 0.8178 | 0.8230 | 0.8495 |
| 2024 | 0.8898 | 0.8780 | 0.8884 | 0.8898 | 0.8875 |
| 2025 † | 0.9311 | 0.8921 | 0.8912 | 0.8895 | 0.8944 |
| **macro** | 0.8159 | **0.8283** | 0.8285 | 0.8295 | **0.8394** |
| **excl. 2025** | 0.7967 | **0.8177** | 0.8180 | 0.8196 | **0.8302** |

† LOW NEGATIVE SUPPORT — 2 undrafted prospects.

Selected board, per fold:

| Year | n | drafted | ROC-AUC | AP | graded NDCG | drafted ρ | drafted τ | P@K |
| --- | --: | --: | --- | --- | --- | --- | --- | --- |
| 2019 | 76 | 40 | 0.7882 | 0.8008 | 0.8831 | 0.3083 | 0.2128 | 0.7250 |
| 2020 | 65 | 40 | 0.6990 | 0.7611 | 0.8126 | 0.0760 | 0.0462 | 0.7000 |
| 2021 | 188 | 50 | 0.7203 | 0.4756 | 0.7281 | 0.3624 | 0.2571 | 0.5000 |
| 2022 | 132 | 43 | 0.6564 | 0.5333 | 0.8024 | 0.5237 | 0.3533 | 0.4651 |
| 2023 | 79 | 41 | 0.7323 | 0.7438 | 0.8021 | 0.2510 | 0.1780 | 0.6829 |
| 2024 | 49 | 33 | 0.6591 | 0.7785 | 0.8780 | 0.1925 | 0.1402 | 0.7576 |
| 2025 † | 28 | 26 | 0.7308 | 0.9726 | 0.8921 | 0.2328 | 0.1938 | 0.9615 |

K = the number actually drafted that year. `recall_at_top25` (K = top 25% of the board) averages 0.3553.

---

## 9. Stage A-only benchmark

Macro ROC-AUC 0.6986 · macro AP 0.7127 · graded NDCG 0.8159 · drafted Spearman 0.2461 · P@K 0.6792 · **graded fold SD 0.0869** · **graded worst year 0.6590**.

This is the board DraftLens would ship if Stage B failed, and it remains a perfectly respectable one. Its distinguishing weakness is instability: it is the **least stable** board tested, and its worst class (2021, the COVID cohort, 0.6590) is the worst single result of any candidate.

---

## 10. Incremental value of Stage B

Fold-by-fold deltas against the Stage A-only board, **excluding the 2-negative 2025 fold** (the honest comparison):

| Config | graded Δ | wins | worst Δ | AUC Δ | wins | ρ Δ | wins | worst Δ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| E_LEXICOGRAPHIC | +0.0335 | 4/6 | **−0.0023** | +0.0034 | 3/6 | +0.0304 | **6/6** | **+0.0129** |
| D_RANK_FUSION | +0.0228 | 3/6 | −0.0412 | **+0.0097** | 4/6 | **+0.0891** | **6/6** | +0.0240 |
| F_EQUAL_WEIGHT_SUM | +0.0214 | 3/6 | −0.0403 | +0.0063 | 4/6 | +0.0805 | 6/6 | +0.0335 |
| C_MULTIPLICATIVE \| PCT | +0.0213 | 3/6 | −0.0419 | +0.0045 | 3/6 | +0.1012 | 6/6 | +0.0301 |
| **C_MULTIPLICATIVE \| UTILITY** | **+0.0210** | **5/6** | **−0.0118** | **+0.0096** | **4/6** | +0.0434 | 5/6 | −0.0028 |
| B_STAGE_B_ONLY | −0.0059 | 2/6 | −0.0280 | −0.0408 | 1/6 | +0.0781 | 6/6 | +0.0058 |

**The selected board is the only candidate positive on all three axes with consistent fold support**: graded NDCG improves in **5 of 6** folds (every other combination is a coin flip at 3/6), AUC in 4 of 6, Spearman in 5 of 6 — with the smallest graded downside of any multiplicative or fusion rule (−0.0118 against −0.041 for the alternatives).

Including 2025 the counts are 5/7, 5/7 and 5/7 respectively.

---

## 11–13. Metric summary for the selected board

**Binary** (drafted vs undrafted): macro ROC-AUC **0.7123**, pooled **0.6830**, macro AP **0.7237**, P@K(drafted) **0.6846**, Recall@top-25% **0.3553**.

**Draft order** (drafted only): Spearman **0.2781**, Kendall **0.1973**.

**Graded full board**: NDCG **0.8283**, fold SD **0.0594**, worst year **0.7281**.

**No Brier or log loss is reported for the board signal.** It is a ranking score, not a probability; scoring it as one would be exactly the false precision this project has refused since DEC-089. Brier remains meaningful only for Stage A.

---

## 14. Temporal stability

| Board | graded SD | graded worst | AUC (all) | AUC (excl. 2025) | shift |
| --- | --- | --- | --- | --- | --- |
| A only | 0.0869 | 0.6590 | 0.6986 | 0.6997 | +0.0011 |
| **C \| UTILITY** | **0.0594** | **0.7281** | 0.7123 | 0.7092 | −0.0031 |
| C \| PCT | 0.0648 | 0.7406 | 0.7244 | 0.7041 | **−0.0203** |
| D fusion | 0.0635 | 0.7421 | 0.7234 | 0.7094 | −0.0140 |
| E lexico | 0.0545 | 0.7420 | 0.7015 | 0.7030 | +0.0015 |

The `shift` column is why `C_MULTIPLICATIVE | WITHIN_BOARD_PERCENTILE` was not selected despite topping the raw AUC table: **most of its apparent AUC advantage disappears when the degenerate 2025 fold is removed** (0.7244 → 0.7041, a −0.0203 shift, the largest of any candidate). The selected utility variant shifts only −0.0031 — its advantage is not a 2025 artifact.

## 15. COVID and 2025 interpretation

**2021 and 2022** (the COVID eligibility cohorts, 320 of 887 development rows) are the hardest classes for every board. Mean graded NDCG across the two: Stage A only **0.7306**; every combination **0.7652–0.7716**. The selected board scores 0.7652. Stage B's contribution is largest exactly where Stage A struggles most — 2021 is the single biggest per-fold gain (+0.0691).

**2025** has 26 drafted and **2 undrafted** prospects. Its binary ROC-AUC and average precision are near-meaningless and are excluded from every selection judgment in this report (DEC-075). Its draft-order metrics are well posed and were used. Notably, Stage A-only scores its *best* graded NDCG on 2025 (0.9311) — a board that looked good only because of that fold would have been selected wrongly, which is why §10 reports the excluding-2025 comparison as primary.

---

## 16. Selected General Board method

```
stage_b_quality    = (draft_size + 1 − clip(predicted_pick, 1, draft_size)) / draft_size
final_board_signal = stage_a_probability × stage_b_quality
```

**Why this one.**

1. **It is a real expectation, not a blend.** *Probability of entering the draft × conditional quality of the slot the profile resembles.* Every alternative that scored comparably is a rank heuristic with no such reading. This is the criterion that separated it from `D_RANK_FUSION`.
2. **It improves both sub-objectives**, unlike Stage B alone (worse binary) or `E_LEXICOGRAPHIC` (negligible binary gain).
3. **It is the most consistent candidate** — the only one improving the joint objective in 5 of 6 non-degenerate folds; every other combination is 3/6.
4. **Its advantage does not depend on the degenerate fold** (AUC shift −0.0031 vs −0.0203 for the percentile variant).
5. **It has no free constants.** No weight, no band width, no curvature. The clipping bound is the basketball-valid slot range.
6. It cuts Stage A-only's fold SD by a third and lifts its worst year by +0.069.

### Why the alternatives lost

| Rejected | Why |
| --- | --- |
| **A_STAGE_A_ONLY** | Beaten on all three headline metrics, and by far the least stable board (SD 0.0869, worst year 0.6590). |
| **B_STAGE_B_ONLY** | Worse than Stage A on the joint objective (graded NDCG −0.006, improving in only 2 of 7 folds) and much worse on binary AUC (−0.041). Trained only among drafted players; models no draft likelihood. |
| **C \| WITHIN_BOARD_PERCENTILE** | Best raw AUC (0.7244) but **−0.0203 of it evaporates without the 2-negative 2025 fold**; also costs 0.042 graded NDCG on 2020. Multiplying a probability by a *rank* also forfeits the expected-value interpretation that motivates method C. |
| **D_RANK_FUSION** | Genuinely strong (best pooled AUC, largest Spearman gain of the fusion rules) but a coin flip on the joint objective (3/6) with a −0.041 worst-case, and it is an explicit heuristic with no expected-value reading. |
| **E_LEXICOGRAPHIC** | Highest graded NDCG (0.8395) and the safest downside — but it improves binary AUC by only **+0.0034** and has the weakest Spearman gain of any combination. Decisively, its output depends on a **band-width constant with no justification**: deciles were predeclared, but quintiles or 20-tiles would give a different board and nothing in the data selects among them. Rejected as too arbitrary, exactly as the brief anticipated. |
| **F_EQUAL_WEIGHT_SUM** | The naive alternative, included as a reference. Slightly worse than D on every axis and, being a weighted sum of two differently-scaled quantities, has no interpretation at all. |

---

## 17. Overall Score transformation

Two transforms were implemented and compared:

| Transform | overall range | mean class max | mean class min | **class median spread** | distinct values |
| --- | --- | --- | --- | --- | --- |
| **CURRENT_BOARD_PERCENTILE** | 0–100 | 99.1 | 0.9 | **0.0** | 101 |
| HISTORICAL_EMPIRICAL_PERCENTILE | 0–100 | 98.3 | 0.7 | **25.0** | 101 |

`class median spread` is how much the median score moves between draft classes. A class-relative score pins every class to the same median by construction; the historical variant lets a genuinely weaker class score lower — a real advantage, and the reason it was implemented.

**Selected: `CURRENT_BOARD_PERCENTILE`.**

```
overall_score = round(100 × within-class percentile of final_board_signal)
```

The historical variant was **rejected on a specific, documented risk**: its absolute meaning rests on the board signal distribution transferring across classes, and that signal is built from Stage A's probability scale. ML_SPEC §4.3 and DEC-066 establish that Stage A is **badly miscalibrated** on a class whose base rate differs sharply from the 48.6% training window — declared-entrant class composition varies by a factor of six across development alone. An absolute score would silently inherit that miscalibration and present it as cross-class comparability it does not have.

The class-relative score depends only on **ordering within a class**, which is exactly what both stages were validated on. Its limitation — scores are not comparable across draft classes — is real, and is disclosed rather than engineered away.

**Score properties**, all enforced by test and validator:

- **Integer 0–100.** No decimals: `92.738` implies precision the model does not have.
- **Order-preserving.** If A ranks above B on the board signal, `score(A) ≥ score(B)`. Verified in all 7 development classes.
- **Deterministic ties.** Equal signals get equal scores. Integer rounding may also tie two close-but-distinct signals; the continuous board signal remains the authoritative order. Ties are **never** broken by player name, draft outcome or any NBA information.

---

## 18. Score semantics

> **DraftLens Overall Score is a 0–100 ranking score derived from historical pre-draft models. It is not a probability and it is not a predicted pick.**

Specifically prohibited: labelling it *Draft Probability*, *chance of being drafted*, or *Predicted Pick*. "92/100 means a 92% chance" is false and must never appear.

Because the score is class-relative, the correct reading is: **"this prospect sits in the top X% of this draft class on DraftLens's pre-draft evidence."**

**Worked example, using development history only.** In the 2024 development class (49 in-scope early entrants), the selected board ranked Reed Sheppard first with an Overall Score of 99 — he was actually drafted 3rd. Zach Edey scored 97 and went 9th. The third-ranked prospect scored 95 and went undrafted. That last case is the honest reading of the score: **95 means "third-strongest profile in this class", not "95% likely to be drafted"** — and the board is wrong about individual prospects regularly, which is why the score is decision *support*.

---

## 19. Missing Stage B handling

**Policy: a prospect Stage A can score is never dropped because Stage B failed.**

A missing Stage B signal receives the **neutral** quality value (0.5 for percentile transforms, the board median for the utility transform), so the combined signal degenerates to a monotone function of Stage A alone for that prospect and their Stage A ordering is preserved.

The rejected alternative — treating a missing signal as a *low* value — would be actively harmful: unresolved and missing-data rows were disproportionately undrafted historically (all 8 unresolved development prospects are undrafted, DEC-071), so a penalty would turn missingness into a hidden outcome proxy. That is the same failure mode that excluded date of birth (ML_SPEC §8.2).

**No empirical comparison was possible:** 0 of 617 development out-of-fold prospects have a missing Stage B signal. The policy is therefore enforced by test rather than selected by measurement, and this is stated rather than glossed.

---

## 20. Product-facing signal definitions

Three **separate** signals, never collapsed into one label:

| Signal | Source | What it is | What it is NOT |
| --- | --- | --- | --- |
| **Overall Draft Score** | ML-6 board | Integer 0–100 ranking score within the class | not a probability, not a pick |
| **Draft Probability** | Stage A | P(drafted) — the only genuine probability DraftLens produces | not a board rank |
| **Draft Position Signal** | Stage B | Conditional draft-order signal | **not a "Predicted Pick"** (DEC-089) |

**Recommended terminology** for the Draft Position Signal — final UI choice deferred: *Draft Position Signal*, *Early / Mid / Late draft tendency*, *Relative Draft Ranking*. The ML-5 three-tier scheme (lottery / rest of R1 / round 2; 42% exact, 79% adjacent accuracy) is available as a **secondary explanation** only. It is not used to build the Overall Score.

---

## 21. Limitations

1. **The incremental value of Stage B is modest** — +0.012 graded NDCG, +0.014 binary AUC. The case rests on consistency (5 of 6 folds) and stability, not on the size of the gain.
2. **Stage A-only remains a defensible board.** A reviewer preferring maximum simplicity would not be wrong to ship it; it is beaten, not embarrassed.
3. **The board is wrong about individual prospects regularly.** Binary AUC 0.7123 and drafted Spearman 0.2781 are real but modest. Workouts, medicals, interviews and team need are not in this data.
4. **2020 is a weak fold for every combination** (drafted Spearman 0.076) — the pandemic-shortened NCAA season leaves a genuinely thinner statistical record.
5. **2021 remains the worst class** (graded NDCG 0.7281) even after combination.
6. **The Overall Score is class-relative** and not comparable across draft classes. Every class necessarily contains a ~100 and a ~0.
7. **Stage B extrapolation to undrafted prospects is unvalidated by construction** — there is no ground-truth pick for them, so §5 audits distributional plausibility, which is not the same as correctness.
8. **Board metrics cover in-scope NCAA early entrants only** — not seniors, not international prospects. DraftLens does not reproduce the real NBA draft board.
9. **No 2011–2013 robustness analysis was run.** The ML-6 board depends on out-of-fold Stage A and Stage B signals produced by the expanding-window protocol, and that protocol has no fold whose *training* years precede 2011–2013. Constructing one would require training on later years and evaluating earlier ones — temporally invalid. This is stated rather than forced for symmetry.

---

## 22. 2026 firewall

No 2026 target was loaded. No 2026 Stage A probability, Stage B signal, board, ranking or Overall Score was generated. No 2026 pick was inspected. No formula, transform or scaling constant was chosen with any reference to 2026 — the historical score reference distribution, had it been selected, was built from development out-of-fold signals only.

Enforced by: validator check 3 (population, board, artifacts and source scanned), `TestHoldoutFirewall` in `tests/ml/test_board.py`, and `assert_no_holdout` inside both stage entry points.

## 23. Next phase

**ML-7 — Team Need analytical scoring.**

Team Need is a **deterministic multi-criteria ranking**, not a predictive model, and it must never reuse the General Draft Board's output (DEC-006, ML_SPEC §19.1). User weights are preferences and must never be fitted to data.

Also still open: NBA statistical comparables; the application layer; and the ML-8 holdout run, which is the only phase permitted to open 2026.

The 2026 holdout remains sealed.
