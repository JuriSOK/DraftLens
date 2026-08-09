# DraftLens — ML-2 Report: transparent basketball feature layer

**Status:** Complete. **No model was trained; no score was calculated.**
**Date:** 2026-08-08 · **Phase:** ML-2 ([ML_SPEC.md](../ML_SPEC.md) §27)

```bash
./.venv/bin/python scripts/build_features.py --reference
./.venv/bin/python scripts/experiments/validate_ml2_features.py
./.venv/bin/python -m unittest discover -s tests
```

Companion documents: [ML_SPEC.md](../ML_SPEC.md), [ML1_EDA.md](ML1_EDA.md), [ML0_DATASET.md](ML0_DATASET.md), [DECISIONS.md](../DECISIONS.md). Formulas are contractually documented in [`config/features/feature_dictionary.csv`](../../config/features/feature_dictionary.csv) — that file, not this report, is the source of truth.

---

## 1. Executive summary

**61 engineered features** across 12 families, built on all **887 development / 125 robustness / 26 holdout** prospects. Validation: **0 hard failures**, 1 documented warning. **103 tests pass.**

The layer is complete: possession reconstruction succeeded, so **usage%, AST%, TOV%, ORB%, DRB%, TRB%, STL% and BLK% are all implemented** rather than deferred. Reconstructed team minutes come to **201.4 per game** against a theoretical 200, and every rate lands in textbook range (usage median 24.2%, TS% 0.57, DRB% 16.8).

**Three findings matter for ML-3.**

1. **No new leakage.** Strongest engineered separator is `tip_attempt_share` at rank-AUC **0.644** — weaker than ML-1's raw `unassisted_dunk_makes` (0.687). Nothing behaves like a hidden outcome.
2. 🟠 **Undefinedness of rare-event ratios tracks the target.** `tip_make_pct` is defined for **77.5% of drafted but 50.4% of undrafted** — a **27.1 pp** gap. This is not contamination: attempting zero tip-ins is itself informative. But it means imputing these with a constant, or adding a missingness indicator, would inject a partial target proxy.
3. 🟠 **23 feature pairs correlate ≥ 0.95**, four of them at exactly 1.000 — algebraic complements kept deliberately so ML-3 can choose the representation.

**Nothing was selected, weighted, scaled or combined.** These are ingredients.

## 2. Engineered feature families

| Family | n | Content |
| --- | --: | --- |
| PLAYMAKING | 9 | assists/turnovers per game, per 40, per 100, AST/TO, AST%, TOV% |
| DEFENSIVE_PRODUCTION | 9 | steals/blocks per game, per 40, per 100, fouls per 40, STL%, BLK% |
| SHOT_PROFILE | 9 | layup/dunk/tip/three/rim attempt shares and make percentages |
| REBOUNDING | 8 | per game, per 40 (O/D/total), per 100, ORB%, DRB%, TRB% |
| SHOOTING_EFFICIENCY | 6 | FG%, 2P%, 3P%, FT%, eFG%, TS% |
| SHOOTING_VOLUME | 6 | 3PA/2PA/FT rates, FGA/3PA/FTA per 40 |
| CREATION | 6 | assisted and unassisted shares overall, layups, dunks |
| SCORING | 3 | points per game, per 40, per 100 |
| PLAYING_TIME | 2 | minutes per game, start share |
| PHYSICAL | 2 | height, weight |
| ROLE | 1 | usage% |
| POSITION | 1 | position_3 (G/F/C/UNKNOWN) |

Alongside these: **10 denominators** (`minutes`, `field_goals_attempted`, `three_points_attempted`, `free_throws_attempted`, `games_played`, `shot_records`, `fg_attempts_shotfile`, `team_minutes`, `team_possessions`, `opp_possessions`) retained so ML-3 can reason about small-sample reliability, and **3 audit fields** (`shot_fga_coverage_ratio`, `n_teams`, `experience_years`) explicitly outside the predictive set.

## 3. Exact formulas

All 70 dictionary rows carry formula, source columns, denominator, unit, missing behaviour, position/season sensitivity and status. Representative entries:

```
efg_pct   = (FGM + 0.5*3PM) / FGA
ts_pct    = PTS / (2 * (FGA + 0.44*FTA))
usage_pct = 100 * ((FGA + 0.44*FTA + TOV) * (TmMP/5))
                 / (MP * (TmFGA + 0.44*TmFTA + TmTOV))
ast_pct   = 100 * AST / (((MP / (TmMP/5)) * TmFG) - FG)
tov_pct   = 100 * TOV / (FGA + 0.44*FTA + TOV)
orb_pct   = 100 * (ORB * (TmMP/5)) / (MP * (TmORB + OppDRB))
blk_pct   = 100 * (BLK * (TmMP/5)) / (MP * (OppFGA - Opp3PA))
```

**The 0.44 free-throw possession coefficient** appears in TS%, possessions, usage% and TOV%. It is the conventional approximation of the share of free-throw trips that end a possession, exposed as a named constant (`FT_POSSESSION_COEF`) rather than buried as a literal. Free throws are taken **only** from `player_box` — the shot file contains made free throws exclusively (DATA.md §22.3).

## 4. Team and possession reconstruction

Team and opponent totals are summed over **each prospect's played games only**, never a whole-season team total, so a transfer's context follows them and no unplayed game leaks in.

```
team-game totals  = sum of player_box rows by (game_id, team_id)
opponent totals   = self-join on game_id where team_id differs
prospect context  = sum over the prospect's played (game_id, team_id) rows
possessions       = FGA + 0.44*FTA - ORB + TOV
```

**Validation:** reconstructed **team minutes per game = 201.4** (theoretical 200 — the excess is overtime). Team possessions median 2,232 over ~33 games ≈ **68 per game**, correct for NCAA pace. This confirms DATA.md §22.2's finding that `team_box` is unnecessary.

## 5. Shooting efficiency

FG%, 2P%, 3P%, FT%, eFG%, TS% all implemented. Development medians: **TS% 0.571, eFG% 0.534, FG% 0.462** — textbook NCAA values. Coverage 97.8% except **3P% at 92.6%**, undefined for players who attempted no threes. That undefinedness is correct and must not be filled with 0.

## 6. Playmaking

AST%, TOV%, AST/TO, and per-game/per-40/per-100 assists and turnovers. AST% median **12.99** (max 51.9), TOV% median **13.92** — both plausible. `assist_to_turnover_ratio` is undefined for zero-turnover players (97.8% coverage) rather than infinite.

## 7. Rebounding

**ORB%, DRB%, TRB% implemented** — the opponent denominators reconstructed cleanly. Medians **ORB% 5.34, DRB% 16.82, TRB% 11.40**, all in expected range. Per-40 and per-100 variants retained as alternatives; §15 shows `oreb_per_40` and `orb_pct` correlate at 0.993, so ML-3 should keep one.

## 8. Defensive production

STL%, BLK% and per-40/per-100 counts implemented. BLK% median **1.90**, max **19.07** (centres). STL% median **1.86**.

> These measure **box-score defensive production**, not defensive quality. There is no matchup, opponent-shooting, on/off or deterrence data. No feature is named `defense_quality`, `elite_defender` or `defensive_rating`, and none may be (DEC-055).

`blocks_per_40` remains the ML-1 oddity — correlating only 0.07 with minutes — so it is position-driven and needs position-relative treatment.

## 9. Shot profile

Built **only from stable categories** (DEC-068): layup, dunk, tip, and three-point shots identified via `score_value` rather than `type_text`. Attempt shares use the prospect's shot-file FGA universe.

**No generic jump-shot feature exists.** `jump_shot_share`, `jump_shot_pct` and `jump_shots_per_40` are recorded in the dictionary with status `REJECTED` so the reason survives, and a test fails if any column containing `jump_shot` reaches the feature layer.

`shot_fga_coverage_ratio` (shot-file FGA ÷ box FGA, median ≈ 0.96) is **audit metadata, not a feature** — data completeness must not become a predictive signal.

## 10. Assisted / unassisted creation

Six features from shot-event assist linkage, which ML-1 measured as stable at **50.8–52.9%** league-wide across all 12 years. Only **made** field goals are used; no assisted-attempt rate is invented. `unassisted_layup_make_share` is the feature that distinguishes a self-creating slasher from a play-finisher.

## 11. Physical and position policy

`height` and `weight` retained raw and **not season-normalised** — ML-1 measured relative drift of 0.038 and 0.071, i.e. stable. No BMI derived, since no basketball reason was documented.

Position is **`position_3` ∈ {G, F, C, UNKNOWN}** from hoopR only (DEC-067). Development distribution G 449 / F 356 / C 64 / UNKNOWN 18. No PG/SG/SF/PF/C label was created or inferred; `position_from_population` was never read.

## 12. Missingness

No imputation, no missingness indicators, no zero-filling of undefined ratios.

| Feature | Coverage |
| --- | --: |
| `tip_make_pct` | **63.6%** |
| `assisted_/unassisted_dunk_make_share` | 89.0% |
| `dunk_make_pct` | 90.2% |
| `three_point_pct` | 92.6% |
| Most box-derived features | 97.8% |
| `height`, `weight` | 98.4% |

Coverage is reported overall, by year and by `position_3` in `data/interim/ml2/audit_coverage*.csv`. Worst season-level cell is `tip_make_pct` at 40.8%.

### 🟠 Undefinedness tracks the target

| Feature | Drafted | Undrafted | Gap |
| --- | --: | --: | --: |
| `tip_make_pct` | 77.5% | 50.4% | **+27.1 pp** |
| `assisted_dunk_make_share` | 95.8% | 82.5% | +13.3 pp |
| `unassisted_dunk_make_share` | 95.8% | 82.5% | +13.3 pp |
| `dunk_make_pct` | 96.3% | 84.4% | +11.9 pp |
| `three_point_pct` | 95.4% | 89.9% | +5.5 pp |
| everything else | ≈99.3% | ≈96.5% | ≈+2.8 pp |

This is **structural, not contamination**: attempting zero dunks or tip-ins is a real basketball fact that correlates with draft stock. But the consequence is concrete — **a constant imputation or a missingness indicator on these features would inject a partial target proxy**, exactly the failure mode that excluded age (DEC-044). ML-3 must handle them with model-native missing support or exclude them; all four are marked `CAUTION` in the dictionary.

## 13. Low-sample reliability

Low-minute prospects were **not dropped**. Instead every ratio ships alongside its denominator, so ML-3 can apply minimum-attempt eligibility, shrinkage, or model-native handling without re-deriving anything. Development minutes range 16–1,374; a 3P% computed from two attempts is stored, and `three_points_attempted` sits beside it to say so.

No threshold was chosen here.

## 14. Temporal stability

Derivation is per-prospect-season and involves no cross-season fitting, so no temporal leakage is introduced. **No pooled scaler was fitted and no z-scoring applied** — that belongs inside ML-3's folds. Season normalisation remains justified by ML-1's drift findings but is deliberately not performed.

## 15. Redundancy groups

**23 pairs at |r| ≥ 0.95**, in `data/interim/ml2/audit_redundancy.csv`. The clearest groups:

| Group | |r| | Note |
| --- | --: | --- |
| `assisted_*_share` ↔ `unassisted_*_share` (3 pairs) | **1.000** | Exact algebraic complements — keep one per pair |
| `three_point_attempt_rate` ↔ `two_point_attempt_rate` | **1.000** | Complements by construction |
| `three_point_attempt_rate` ↔ `three_point_shot_attempt_share` | 0.999 | Box-derived vs shot-file-derived; keep the box version |
| `*_per_game` ↔ `*_per_100` (blocks, assists, steals, rebounds) | 0.99+ | Same quantity, different denominator |
| `steals_per_40` ↔ `stl_pct` | 0.993 | Possession rate adds little over per-40 |
| `oreb_per_40` ↔ `orb_pct` | 0.993 | Same |

Both members of each pair were kept **deliberately** — ML-3 should choose one representation per group on temporal-validation evidence, not by an arbitrary correlation cut here.

## 16. Leakage sanity audit

Development only; the 2026 target file was never opened.

| Check | Result |
| --- | --- |
| Strongest separation | `tip_attempt_share` rank-AUC **0.644** |
| Next | `ts_pct` 0.631 · `blocks_per_100` 0.623 · `blocks_per_game` 0.622 · `dunk_attempt_share` 0.622 |
| Infinities | **0** |
| Out-of-range percentages | **0** |
| Forbidden columns | **0** in all three partitions |
| Prospects lost vs ML-0 | **0** |

Engineering *reduced* peak separation (0.687 → 0.644), which is the expected direction: rate conversion removes the opportunity signal that inflated raw counts.

## 17. Rejected and deferred

| Item | Status | Reason |
| --- | --- | --- |
| `jump_shot_share`, `jump_shot_pct`, `jump_shots_per_40` | **REJECTED** | DEC-068 — `type_text` schema breaks at 2020/21 |
| PG/SG/SF/PF/C features | **REJECTED** | DEC-067 — no leakage-safe source |
| Age / DOB / DOB indicators | **REJECTED** | DEC-044 |
| `position_from_population`, `class_from_population`, `match_method` | **REJECTED** | DEC-065 |
| `experience_years` | **DESCRIPTIVE ONLY** | Semantics unverified across seasons; retained outside the predictive set rather than guessed at |
| `shot_fga_coverage_ratio`, `n_teams` | **AUDIT ONLY** | Data completeness must not become a signal |
| BMI | **NOT DERIVED** | No documented basketball reason |
| Season-normalised columns | **DEFERRED** | Belongs inside ML-3 folds |
| Sub-scores, profile scores, Overall Score | **OUT OF SCOPE** | No weights exist yet |

## 18. NCAA reference-distribution readiness

**Created:** `ncaa_reference_distributions.parquet` — 640 rows covering **16 seasons × 4 coarse positions × 10 metrics**, each with count, mean, std, median, p10, p25, p75, p90.

Built from the **full hoopR NCAA player population** (~10,000 players per season), never from the prospect set, and **draft outcome is never consulted**. No minimum-minute threshold was applied — that choice is deliberately deferred, so the artifact stays reusable.

This supports later position-relative interpretation, strengths/weaknesses percentiles, and Team Need context. It is **not** joined into the prospect feature table.

## 19. 2026 holdout guard

The feature builder **never reads a target file** — enforced by a test that inspects every `read_parquet` call in the script. 2026 features are produced by identical formulas with no branch on partition, and the validator refuses `load_targets_guarded("2026")`.

Holdout: 26 rows, schema identical to development, disjoint prospect set. **No target-aware missingness, effect size, correlation, feature choice or threshold was computed on 2026.**

## 20. ML-3 readiness

**Ready.** Recommended scope: **BASELINES AND PREPROCESSING EXPERIMENTS ONLY.**

ML-3 should:
1. Establish the five ML_SPEC §15 baselines on the expanding-window folds.
2. Compare preprocessing strategies — season normalisation, position-relative normalisation, missing-value handling — **fitted inside folds only**.
3. Resolve one representation per redundancy group (§15).
4. Decide handling for the four `CAUTION` features whose undefinedness tracks the target (§12).
5. Choose minimum-attempt eligibility or shrinkage using the retained denominators (§13).

ML-3 must **not** touch 2026, must not select features by predictive performance before baselines exist, and must respect DEC-065/067/068/044.
