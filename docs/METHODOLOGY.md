# DraftLens — Methodology

The final, frozen system. This describes what DraftLens does today, not the
chronology that produced it — that record lives in git history.

## 1. Overview

DraftLens answers one narrow, checkable question about a declared NCAA early
entrant, using only information available before a given draft:

> Given the objective pre-draft record, which prospects does it support, and
> how highly?

Three independent products answer related but distinct questions:

| Product | Question | Ground truth? |
| --- | --- | --- |
| **General Draft Board** | Overall prospect quality by the objective record | Yes — historical draft outcomes |
| **Team Need** | Fit against specific requested traits | No — descriptive, preference-based |
| **NBA Comparables** | Which NBA players statistically resemble this prospect | No — descriptive resemblance only |

All three read the same engineered feature layer (`src/features/basketball.py`)
and the same leakage rules (`src/validation.py`); none of them can reach a
draft outcome, an NBA career result, or the 2026 holdout except where
explicitly and narrowly noted below.

## 2. General Draft Board

`src/board/` — `probability.py`, `order.py`, `scoring.py`, `preprocessing.py`.

### 2.1 Draft Probability

P(drafted) for a declared NCAA early entrant. **Frozen** (`board.probability.
DRAFT_PROBABILITY`):

```
Logistic regression | SET_2_BOX_SHOT_PROFILE | SEASON_RELATIVE
| train-fold median imputation | position_3 one-hot
| class_weight="balanced" | C=0.25 | uncalibrated
```

- **Logistic regression** over tree ensembles: the strongest random forest
  candidate owed its lead to a single fold with two negative examples, and
  fell from rank 1 to rank 12 once that fold was removed.
- **SEASON_RELATIVE** — each covered metric is replaced by its z-score against
  the full NCAA population of that same season and coarse position, computed
  from `data/interim/features/ncaa_reference_distributions.parquet`. The only
  representation change that improved the model on evidence (11 of 12
  measures over the prior incumbent). Leakage-safe on three counts: the
  reference is the full season population, not the prospect sampling frame;
  season Y prospects are normalized against season Y only, whose games
  conclude before the June draft; and the identical formula applies to every
  draft year, train and validate alike.
- **`class_weight="balanced"`** — costs ~0.001 macro ROC-AUC and improves
  Brier and ECE materially; the product obligation here is a usable
  probability, not a bare ranking.
- **Uncalibrated** — the fitted model is already the best-calibrated logistic
  model on ECE; every calibration layer costs a training year and compresses
  the usable probability range.

### 2.2 Draft Order

Among **drafted** early entrants only, how highly a profile suggests the
prospect was selected. **Frozen** (`board.order.DRAFT_ORDER`):

```
Ridge(alpha=10) | RAW_PICK target | STANDARD representation
```

- The population is drafted early entrants only (431 of 887); undrafted
  prospects are **removed, never given a synthetic pick** — assigning one
  would invent data and distort the loss surface.
- **The target barely matters.** RAW_PICK, PICK_PERCENTILE and DRAFT_VALUE are
  affine images of one another within a draft year, so a linear model induces
  the same ranking from any of them (measured rank correlation 0.998). Only
  LOG_PICK is genuinely non-affine, and it performs worse.
- **STANDARD, not SEASON_RELATIVE.** The representation was declared to
  inherit Draft Probability's SEASON_RELATIVE form, but the original
  evaluation never actually applied it — every published number was measured
  on STANDARD. STANDARD is recorded as frozen because it is what the evidence
  supports; switching to SEASON_RELATIVE moves macro Spearman from 0.2968 to
  0.2999, which is a scientific change requiring its own evaluation phase, not
  a refactor.
- **The output is an ORDERING, not a displayable number.** MAE is 13.3 picks
  on a 60-pick draft; 21% of predictions land within 5 picks; the model can
  emit an illegal predicted pick (observed minimum −5.1); lottery and
  second-round predictions compress to within 6 picks of each other. A
  numeric predicted pick must never reach a user.

### 2.3 General Board formula

`src/board/scoring.py` combines the two frozen signals — Draft Probability
(trained on all early entrants) and Draft Order (trained on drafted prospects
only, but applied to every prospect on the board). Applying Draft Order to a
historically-undrafted prospect is legitimate and means one specific thing:
*"if this profile were draftable, which part of the draft does it
resemble?"* — never a claim the prospect will be drafted.

```
draft_slot_utility(pick, size) = (size + 1 − clip(pick, 1, size)) / size
final_board_signal            = draft_probability × draft_slot_utility
```

`C_MULTIPLICATIVE` (**frozen**, `GENERAL_BOARD["method"]`) is preferred over
any weighted sum: it reads as an expectation (probability of entering the
draft × conditional quality of the resembled slot), so no fitted blend weight
is needed between two differently-scaled quantities. Missing Draft Order
predictions receive a neutral fallback rather than a penalty — rows with
missing basketball data were disproportionately undrafted historically, so
penalizing missingness would smuggle the outcome back in as a feature.

### 2.4 Overall Score

`final_board_signal` → an integer **0–100** via `CURRENT_BOARD_PERCENTILE`
(percentile rank within that board, mid-rank ties, never exactly 0 or 100).
Order-preserving by construction — score order can never disagree with board
order — and ties are never broken by name, outcome, or NBA information.
**Not a probability and not a predicted pick.**

## 3. Team Need

`src/team_need/` — `dimensions.py`, `scoring.py`, `reference.py`,
`profiles.py`, `explanations.py`, `validation.py`.

Team Need is **not predictive**. There is no ground-truth target, so nothing
here is optimized against draft outcomes, the General Board, or NBA career
success. It answers a factual question — *how well does this prospect's
statistical record match a set of requested traits?* — against a peer
population, and nothing else.

### 3.1 Dimensions

Six factual dimensions, each a peer percentile against the full NCAA
population of that season and coarse position (not just draft prospects):
**Shooting**, **Playmaking**, **Box-score Defensive Production**,
**Rebounding**, **Size**, **Rim Pressure**. **Athleticism is explicitly
`UNAVAILABLE`** — no athleticism measurement exists in any source, and no
box-score proxy (dunk rate, etc.) is substituted for it. A request for it is
refused (`UnsupportedNeed`), never silently degraded.

### 3.2 Profiles

Six predefined archetypes (`Shooter`, `Slasher/Rim Attacker`, `Playmaker`,
`3&D Wing`, `Rim Protector`, `Stretch Big`), each a declared combination of
dimensions. Conjunctive archetypes (a prospect must show *both* qualities) use
a **geometric mean**, not an arithmetic one — an arithmetic mean lets a
strength on one axis paper over a near-total absence on the other, which is
exactly wrong for a profile like Rim Protector that requires size *and* shot
deterrence together.

### 3.3 Custom weighted mode

A caller supplies dimension weights directly. Coverage policy: a dimension
missing for a prospect is dropped from that prospect's calculation, never
imputed or zero-filled; if the fraction of the *requested weight* actually
landing on scorable dimensions falls below a declared minimum
(`MIN_SUPPORTED_WEIGHT`), the Fit Score is `UNAVAILABLE` rather than a number
built from a fraction of what was asked.

### 3.4 Fit Score

Integer **0–100**, peer-relative — explicitly *not* a probability, not a
predicted pick, and independent of the General Board (measured historical
correlation between the two rankings: ρ = 0.18–0.62 depending on profile,
confirming Team Need surfaces genuinely different players). Missing evidence
is never scored as 0 or 50 — a filled-in value would be indistinguishable
from real evidence.

### 3.5 Limitations

No athleticism. Size is position-relative and diagnostic rather than an
independent dimension for eligibility. Coverage is peer-relative to the
historical NCAA population, so the same raw statistic can score differently
across seasons that had different league-wide baselines — by design, since
the question is "how good relative to peers," not "how large in absolute
terms."

## 4. NBA Statistical Comparables

`src/comparables/` — `nba_features.py`, `reference.py`, `space.py`,
`similarity.py`, `explanations.py`, `validation.py`.

Purely **descriptive** statistical similarity — explicitly not career
prediction, not a ceiling or floor claim, and never phrased as "will become."
`src/comparables/` never imports a scoring system (verified by test): the
Draft Probability, Draft Order, General Board and Team Need scores are
unreachable from comparable generation.

### 4.1 Common NCAA/NBA space

Raw production is never compared across leagues directly — 19 NCAA points per
game and 19 NBA points per game are not the same event; pace, spacing, role
and competition all differ. Every metric is converted to a **league-relative
percentile**, within its own league and season, before comparison; only the
resulting profile *shapes* are compared.

Six dimensions, deliberately not all "higher is better":

| Dimension | Kind | Reads |
| --- | --- | --- |
| Shooting Efficiency | Quality | higher = more efficient scorer |
| Scoring Role | Role | higher = larger share of the offense |
| Creation | Role | higher = more of a passing/creation role |
| Rebounding | Role | higher = more of a rebounding role |
| Defensive Activity | Role | higher = more box-score defensive events, **not** defensive quality |
| Perimeter Orientation | Style | high = perimeter shot diet, low = interior/contact — **neither end is better** |

That mix is the point: if every dimension were "higher is better," an elite
prospect would simply match elite NBA players regardless of role, and the
system would be a goodness ranking wearing a similarity costume. Ten
NCAA-side metric families were evaluated and rejected for the shared space —
possession-based percentages (AST%, usage%, ORB%/DRB%/STL%/BLK%) because the
NBA long-format schema cannot safely reconstruct team/opponent totals for a
traded player, and the entire rim-pressure family because no NBA shot-location
file exists.

### 4.2 NBA reference

One row per eligible NBA player: ≥750 minutes and ≥30 games across the
2021–2025 reference window (rotation players only), minutes-weighted mean
across their recent seasons (`RECENT_MULTI_SEASON`) — chosen over a
single-latest-season representation (only 42% name overlap with the
multi-season choice) or a full-career representation (75% overlap, but
diagnostic-only: it blurs distinct role eras together for a long-career
player).

### 4.3 Similarity

Coverage-normalized **Euclidean** distance over the shared dimensions (at
least 75% of dimensions must be present on both sides, or the result is
`UNAVAILABLE`). Euclidean was chosen over Manhattan (77% neighbor agreement)
and Cosine (74% agreement, and mathematically undefined for an exactly-average
profile — a real, measured weakness, not a hypothetical one).

The similarity score is an **empirical percentile against a frozen external
reference distribution** of prospect-to-pool distances — not an arbitrary
linear rescale of the raw distance. A simpler alternative (percentile within
the candidate pool itself) was implemented, measured, and **rejected**: with a
fixed pool of 542, the top-3 closest are always the top 0.55% by rank, which
made the transform return nearly identical scores (100.00 / 99.82 / 99.63)
for every prospect regardless of whether the underlying match was tight or
loose. The external-reference transform was verified to discriminate properly
between genuinely close and loose matches.

### 4.4 Exactly three players

`find_comparables` returns exactly three unique NBA players, closest-first,
deterministically tie-broken, with a historical prospect's own eventual NBA
self excluded by normalized-name match. Below the 75% coverage minimum, the
result is `UNAVAILABLE` with no names returned — never a manufactured
comparable built from too little evidence.

### 4.5 Limitations

Individual comparable identities are sensitive: leave-one-dimension-out
stability sits at 45–56% (the *specific three names* often change when one
dimension is removed), and the median gap between the 3rd and 4th closest
match is only ~4% of the raw distance — meaning the third name is frequently
one of several nearly-equally-close candidates. The aggregate methodology is
sound (no single dimension dominates the outcome), but a comparable list is a
**neighborhood**, not three uniquely correct names, and should be read that
way.

## 5. Leakage protection

Two policies, defined once in `src/validation.py` and enforced on every
dataset build and by dedicated tests:

- **Feature-file policy** (`DENY_EXACT`, `DENY_SUBSTRING`) — columns that may
  never be written into the feature file at all.
- **Model-input policy** (`DENIED`, `DENIED_SUBSTR`) — broader: identity keys,
  audit columns, and outcome-correlated metadata that may legitimately exist
  in a file but must never enter a model.

Several exclusions exist because a column's *availability* — not its value —
is decided by the outcome (date of birth, the Wikipedia position/class
labels; see `docs/DATA.md` §7). A missingness indicator for either would be
close to the most target-predictive column in the dataset while carrying zero
basketball information, so no missingness indicator is ever derived for a
denied field.

## 6. Temporal validation philosophy

Random train/test splitting is **prohibited** for evaluation: it would place
same-year, same-class prospects on both sides of a split and destroy the
temporal guarantee a draft evaluation actually needs. Every fold trains on
draft years strictly earlier than the year it validates — seven expanding
folds, 2019 through 2025 (`config/board.json`, enforced by
`validation.folds`). Everything fitted inside a fold — imputation, scaling,
percentile references, the SEASON_RELATIVE representation — is fitted on
training years only, refit fresh inside every fold.

## 7. The 2026 holdout

**The methodology described above was frozen — tagged `analytics-freeze-pre-2026`
on commit `bed3c43` — before any 2026 outcome was opened.** 2026 has since
been used exactly once, as the final holdout evaluation (`src/replay.py`,
`docs/VALIDATION.md` §"2026 final holdout replay"): the frozen models were
fit on 2014–2025, applied to the 26 2026 NCAA early entrants, and the complete
product output was generated, written and SHA-256-hashed before any 2026
draft outcome was loaded. Only after that freeze were the actual outcomes
opened, joined against the frozen predictions in a separate evaluation file,
and the prediction file's hash re-verified unchanged. **No model,
hyperparameter, feature, formula, or score was changed after 2026 outcomes
were seen.**

The firewall that made this possible during development remains structural,
not a convention: `data.build.load_development`, `load_draft_order`, and
`validation.assert_no_holdout` still raise if 2026 reaches an ordinary
training or evaluation path; `scripts/demo.py` still refuses the year
outright. The rule is no longer "2026 cannot be scored" — it is **"2026
scoring is possible only through the explicit, one-time, auditable replay in
`src/replay.py`; actual 2026 outcomes are evaluation-only and were opened
exactly once."** `scripts/build.py replay-2026` (predict, freeze, hash) and
`scripts/build.py replay-2026-eval` (unseal, evaluate) are deliberately
excluded from the ordinary `scripts/build.py` (`all`) run, so a normal build
can never re-trigger either step. The methodology is now closed to further
tuning; the next phase is application integration.

See `docs/VALIDATION.md` for the evidence behind every methodology choice
above.
