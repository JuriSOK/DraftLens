# DraftLens — Technical Architecture

**Status:** Both analytical product modes implemented and frozen — General Draft Board and Team Need. No application layer yet.

This describes what exists. Sections 14–15 describe what does not exist yet and where it will go — they are placeholders by design, not omissions.

---

## 1. Overview

DraftLens turns public pre-draft NCAA data into an explainable evaluation of draft prospects. The analytical core is a Python package; everything else is a thin entry point around it.

Three constraints shape the whole design:

- **Temporal honesty.** No information that postdates the draft being evaluated may influence any output for it — including through feature construction, normalisation constants, imputation fits, hyperparameter choice, or population membership.
- **Explainability over performance.** A method that cannot support per-prospect explanation is at a disadvantage regardless of its metrics.
- **No invented numbers.** Missing data stays missing unless an approved, documented method fills it.

The **2026 draft is a sealed holdout**. Nothing in the pipeline may load it until the designated evaluation phase.

---

## 2. Repository structure

```
DraftLens/
├── src/draftlens/            reusable analytical library
│   ├── paths.py              canonical filesystem locations
│   ├── leakage.py            the single definition of what may never be a feature
│   ├── data/
│   │   ├── population.py     the sampling frame (early entrants only)
│   │   ├── dataset.py        ML-0 prospect-dataset build
│   │   ├── acquisition/      http · manifest · hoopr · wikipedia · wikidata
│   │   ├── identity/         normalization · matching
│   │   └── validation/       raw · audits
│   ├── features/
│   │   ├── rates.py          safe_div, per-40/per-game/per-100, possessions
│   │   ├── shooting.py  playmaking.py  rebounding.py  defense.py
│   │   ├── boxscore.py  shot_profile.py  physical.py  positions.py
│   │   ├── engineering.py    assembles the feature layer
│   │   └── reference.py      NCAA season × position distributions
│   ├── ml/
│   │   ├── datasets.py       loading + holdout firewall
│   │   ├── preprocessing.py  fold-local imputation, scaling, season-relative
│   │   ├── validation.py     temporal folds, holdout guard
│   │   ├── metrics.py        Stage A + Stage B metrics
│   │   ├── baselines.py      the simple models complexity must beat
│   │   ├── stage_a.py        FROZEN — P(drafted)
│   │   ├── stage_b.py        FROZEN — draft-position ranking
│   │   ├── board.py          FROZEN — General Draft Board + Overall Score
│   │   └── guards.py         assertions shared by every validator
│   ├── team_need/            FROZEN — dimensions, profiles, Fit Score
│   └── comparables/          placeholder
│
├── scripts/                  thin CLI entry points
│   ├── acquire_data.py  build_dataset.py  build_features.py
│   ├── run_stage_a.py   run_stage_b.py    validate.py
│   └── experiments/          historical selection experiments + validators
│
├── config/                   data/ · features/ · ml/
├── tests/                    data/ · features/ · ml/ · integration/
├── docs/                     specs + experiments/ (frozen phase reports)
└── data/                     raw/ · interim/ · processed/  (all git-ignored)
```

**The architectural rule:** `src/draftlens/` holds reusable logic; `scripts/` parses arguments, calls the library, prints, and returns an exit code. A formula must never be duplicated in a script.

---

## 3. Data flow

```
        Wikipedia            hoopR (ESPN)            Wikidata
     draft articles      player_box · shots ·      biography
            │             player_core                  │
            ▼                    ▼                     ▼
   ┌────────────────────────────────────────────────────────┐
   │  data/raw/     IMMUTABLE · checksummed in the manifest  │
   │  population/ and targets/ are SEPARATE directories      │
   └────────────────────────────────────────────────────────┘
            │
            ▼
   Identity resolution        name + school → hoopR athlete_id
            │                 ambiguous ⇒ UNMATCHED, never forced
            ▼
   ML-0 prospect dataset      887 prospects · 431 drafted · 456 undrafted
            │                 leakage + population gates run on every build
            ▼
   ML-2 feature layer         transparent basketball features
            │                 + NCAA season × position reference distributions
            ▼
   ┌──────────────────────┬──────────────────────┐
   │       STAGE A        │       STAGE B        │
   │   P(drafted)         │   draft ranking      │
   │   all early entrants │   drafted only       │
   │   887 prospects      │   431 prospects      │
   └──────────────────────┴──────────────────────┘
                      │
                      ▼
            GENERAL DRAFT BOARD
        P(drafted) x draft-slot utility
                      │
                      ▼
          Overall Draft Score  0-100
                      │
                      ▼
              2026 holdout  (SEALED)
```

Every arrow crossing into modelling passes a holdout guard that raises on 2026.

---

## 4. Data acquisition

`draftlens.data.acquisition` — one module per source, separated from parsing and from identity.

| Source | Module | Licence | Provides |
| --- | --- | --- | --- |
| hoopR (ESPN) | `hoopr.py` | CC BY 4.0 | player_box, shots, player_core |
| English Wikipedia | `wikipedia.py` | CC BY-SA 4.0 | draft population, draft results |
| Wikidata | `wikidata.py` | CC0 1.0 | date of birth (display only) |

`http.py` sends a descriptive user agent, throttles, and backs off on 429/5xx. Nothing authenticates, and no paywall or rate limit is circumvented.

`manifest.py` records URL, timestamp, size, SHA-256 and row count for every acquired file in `data/source_manifest.csv`. **Raw data is immutable**; the manifest is how that is verified, and `scripts/validate.py --stage raw` fails if a checksum has moved.

Wikipedia markup for these articles is not uniform — four distinct table styles appear across 2011–2026 — so the parsers handle each explicitly rather than assuming a schema.

---

## 5. Identity resolution

There is no shared key between Wikipedia and hoopR, so prospects are matched on normalised name plus school. `draftlens.data.identity` keeps three keys distinct because they are not interchangeable:

| Key | Role |
| --- | --- |
| `normalize_name` | canonical identity, written once into the raw CSVs — **frozen** |
| `match_key` | matching only; fixes two general defects in the canonical key |
| `norm_school` | program name, used to disambiguate same-name players |

Match order: reviewed override → exact normalised name → school disambiguation → surname + school + first-name-prefix (unique candidate only) → **UNMATCHED**.

**An ambiguous match is never forced.** Match failures concentrate in the undrafted class, so a wrong match is a leakage risk rather than a cosmetic error. Unmatched prospects are **retained** with null statistics — dropping them would selectively remove negatives and inflate every downstream metric.

---

## 6. Feature engineering

`draftlens.features` is organised by basketball meaning, not by phase. Formulas are plain functions with no state.

Three policies are enforced in code:

- **Safe division.** An undefined ratio is NULL — never 0, never infinity, no epsilon. 0 made from 0 attempts is *unknown*, not 0%. Substituting 0 would encode "never attempted" as "attempted and failed", and attempt frequency correlates with the outcome.
- **Team context from played games only.** Team and opponent totals are summed over the games a prospect actually appeared in, reconstructed from `player_box`.
- **Source hazards are designed around.** The shot file contains only *made* free throws, so free-throw metrics come from `player_box`. Shot coordinates carry ±2.1×10⁸ sentinels, so shot style is derived from `type_text`, never coordinates.

`reference.py` builds NCAA season × coarse-position distributions from the **full** NCAA player population — not the prospect frame, and never reading a draft outcome. This powers the season-relative representation.

---

## 7. Stage A — P(drafted)

**Frozen** (`draftlens.ml.stage_a.STAGE_A`):

```
Logistic regression | SET_2_BOX_SHOT_PROFILE (25 features) | SEASON_RELATIVE
| train-fold median imputation | position_3 one-hot
| class_weight="balanced" | C=0.25 | uncalibrated
```

Published performance: macro ROC-AUC **0.6986**, pooled 0.6953, Brier 0.2238, ECE 0.0590, fold SD 0.0281, worst year 0.6742.

Tree ensembles were tested and rejected. The top random forest scored higher overall but owed its lead to a single fold containing two negative examples; removing that fold dropped it from rank 1 to rank 12. Details in [experiments/ML4_STAGE_A.md](experiments/ML4_STAGE_A.md).

---

## 8. Stage B — draft ranking

**Frozen** (`draftlens.ml.stage_b.STAGE_B`):

```
Ridge(alpha=10) | RAW_PICK target | SET_2_BOX_SHOT_PROFILE
| STANDARD representation | train-fold median | position_3 one-hot
```

Population: **drafted early entrants only**. Undrafted prospects are removed, never given a synthetic pick — a sentinel would invent data and distort the loss surface.

Published performance: macro Spearman **0.2968**, Kendall 0.2089, NDCG 0.9043, NDCG@14 0.7555, MAE 13.21 picks.

Two findings constrain how Stage B may be used:

- **The target design barely matters.** Raw pick, pick percentile and normalised draft value are affine images of one another within a draft year, so for a linear model they induce the *same* ranking (measured rank correlation 0.998).
- **The number is not displayable.** MAE is 13.3 picks on a 60-pick draft, only 21% of predictions land within 5 picks, and the model emits picks outside the legal range. **Stage B output is an ordering.** A numeric predicted pick must never reach a user.

> ⚠ ML-5 declared it would inherit Stage A's `SEASON_RELATIVE` representation but never applied it, so every published Stage B number was measured on `STANDARD`. The code records `STANDARD` because that is what the evidence supports. See the correction notice in [experiments/ML5_STAGE_B.md](experiments/ML5_STAGE_B.md).

---

## 9. Validation and the leakage firewall

Four independent layers:

**1. Temporal protocol.** Seven expanding-window folds; training years always strictly earlier than the validation year. Random splitting is prohibited — it would put same-year prospects and same-class team-mates on both sides. Everything fitted inside a fold is fitted on training rows only.

**2. Leakage policy** (`draftlens.leakage`). Two lists, deliberately distinct: what may never be *written* to a feature file, and what may never enter *X*. Several entries leak not through their values but through their *availability*: date of birth is 100% present for drafted and 69% for undrafted prospects; the Wikipedia position label resolves to a five-position value for 100% of drafted versus 7.7% of undrafted. A missingness indicator for either would be the most target-predictive column in the dataset while carrying no basketball information.

**3. Holdout firewall.** `assert_no_holdout` raises rather than warns. The 2026 partition is not loadable from `draftlens.ml.datasets` at all. Tests scan source files to prove the holdout target file is never referenced.

**4. Phase validators** (`scripts/validate.py`). Each stage keeps its own validator because their rules genuinely differ; shared assertions live in `draftlens.ml.guards`. Both Stage A and Stage B validators **re-execute the whole pipeline** and require every fold metric to match to six decimal places.

---

## 10. Generated data policy

Nothing under `data/` is committed except `README.md`, the source manifest and directory markers.

| Path | Contents | Committed |
| --- | --- | --- |
| `data/raw/` | acquired corpus (~200 MB) | no |
| `data/interim/ml0…ml5/` | datasets, features, fold results, predictions | no |
| `data/processed/` | reserved | no |

Trained model binaries and predictions are never committed. Reports in `docs/experiments/` are the durable record; artifacts are reproducible from the scripts.

---

## 11. Experiment history

`scripts/experiments/` holds the selection experiments that produced the frozen choices, plus each phase's validator. They keep phase names because the chronology is part of the evidence — unlike library modules, which are named for what they do.

| Experiment | Report | Established |
| --- | --- | --- |
| `ml1_eda.py` | [ML1_EDA.md](experiments/ML1_EDA.md) | position-label leakage |
| `ml3_baselines.py` | [ML3_BASELINES.md](experiments/ML3_BASELINES.md) | baselines, the benchmark to beat |
| `ml4_stage_a_selection.py` | [ML4_STAGE_A.md](experiments/ML4_STAGE_A.md) | Stage A selection |
| `ml5_stage_b_selection.py` | [ML5_STAGE_B.md](experiments/ML5_STAGE_B.md) | Stage B target + model |
| `ml6_board_selection.py` | [ML6_BOARD.md](experiments/ML6_BOARD.md) | board combination + score |
| `ml7_team_need.py` | [ML7_TEAM_NEED.md](experiments/ML7_TEAM_NEED.md) | Team Need methodology audit |

These reproduce history. They must not be used to change a frozen selection — that requires a new phase and a decision record.

---

## 12. General Draft Board — the combination

**Frozen** (`draftlens.ml.board.BOARD`, DEC-096..100):

```
stage_b_quality    = (draft_size + 1 - clip(pick, 1, draft_size)) / draft_size
final_board_signal = P(drafted) x stage_b_quality
overall_score      = round(100 x within-class percentile of the signal)
```

The signal is a genuine **expected draft value** — likelihood of entering the draft times the conditional quality of the slot the profile resembles. It carries **no fitted weight**; no blend-weight search was performed.

Published performance: binary macro ROC-AUC **0.7123**, graded board NDCG **0.8283**, drafted-only Spearman **0.2781**, fold SD 0.0594, worst year 0.7281.

Stage B earns inclusion but the margin is modest (+0.012 graded NDCG). The case rests on consistency — the joint objective improves in 5 of 6 non-degenerate folds — and on stability: Stage A alone is the least stable board tested (SD 0.0869, worst year 0.6590).

Stage B is applied to **every** prospect, including those who went undrafted. That is a conditional signal — *"if this profile were draftable, which part of the draft does it resemble?"* — never a pick assignment. Targets are untouched. A missing Stage B signal receives a **neutral** value, never a penalty: missing-data rows were disproportionately undrafted, so penalising them would smuggle the outcome back in.

**Three separate product signals, never merged:** Overall Draft Score (0-100 ranking score) · Draft Probability (Stage A, the only real probability) · Draft Position Signal (Stage B, never a literal pick).

## 13. Team Need — the second product mode

**Frozen** (`draftlens.team_need`, DEC-101..105). A deterministic multi-criteria ranking, **not** a predictive model:

```
six dimensions    Shooting · Playmaking · Box-score defensive production
                  Rebounding · Size · Rim pressure
                  each an equal-weight mean of non-redundant metrics,
                  expressed as an NCAA peer percentile (0-100)

six archetypes    Shooter · Slasher · Playmaker · 3&D Wing
                  Rim Protector · Stretch Big
                  conjunctive archetypes use a geometric mean

custom mode       fit_raw = sum(w_i * d_i) / sum(w_i)
                  weights are PREFERENCES, never fitted
```

Percentiles are computed against the **full NCAA player population** of the same season (≥ 200 minutes, ≥ 10 games; 2,941–3,417 players/season), never the prospect frame and never reading a draft outcome.

**It must be able to outrank the board, and it does** — Team Need correlates with the Overall Score at only ρ = 0.18–0.62 across development classes. No board signal enters a Fit Score, and `team_need` never imports the board pipeline.

**Athleticism is UNAVAILABLE and not scored.** There is no athleticism measurement in the data; dunk rate is a style signal, not a vertical leap. A custom request with a positive athleticism weight is rejected, never silently redistributed.

Fit Score is a **peer-relative** integer 0-100 — deliberately unlike the class-relative Overall Score, because re-ranking within a class would destroy the absolute trait meaning percentiles carry.

## 14. NBA comparables (not built)

Destination: `draftlens/comparables/`. NCAA and NBA statistics must not be treated as one environment. The engine must never read board features or targets. Similarity is descriptive, never a career-outcome claim.

## 15. Application layer (not built)

No frontend, backend, database or deployment target has been chosen, and none is required by the analytics. The library is importable and usable independently of any future application — a web layer would consume `draftlens`, never reimplement it.

---

## Reproducing the pipeline

```bash
pip install -e .

python scripts/acquire_data.py --source mbb --years 2011-2026   # ~200 MB, slow
python scripts/acquire_data.py --source population --years 2011-2026
python scripts/build_dataset.py
python scripts/build_features.py --reference
python scripts/run_stage_a.py
python scripts/run_stage_b.py
python scripts/run_board.py                 # General Draft Board
python scripts/run_board.py --year 2024     # one class's board
python scripts/build_team_need_reference.py # NCAA peer percentiles
python scripts/run_team_need.py --profile STRETCH_BIG --year 2024
python scripts/validate.py
python -m unittest discover -s tests -t .
```

Acquisition is the only expensive step and is not needed to read the results — the reports in `docs/experiments/` are self-contained.
