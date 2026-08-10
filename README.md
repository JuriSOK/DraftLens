# DraftLens

**Data-driven NBA Draft decision support — transparent pre-draft NCAA analytics, validated the way a draft actually happens: forwards through time.**

Built for the **AQX Sports Analytics Data Bowl 3.0**.

---

## What it does

DraftLens answers one narrow, checkable question about a declared NCAA early
entrant, using only information available before a given draft:

> Among declared NCAA early entrants, which prospects does the objective
> pre-draft record support, and how highly?

### General Draft Board
Overall prospect quality from two frozen signals: **Draft Probability**
(P(drafted)) and **Draft Order** (among drafted prospects, how highly their
profile suggests they go), combined into a 0–100 **Overall Score**.

### Team Need
A separate, non-predictive ranking against the specific traits a team is
looking for — six basketball archetypes plus a custom weighted mode, scored
as peer percentiles against the full NCAA population. Not a re-weighting of
the board: historically the two rankings correlate at only ρ = 0.18–0.62, and
each archetype surfaces different players.

### NBA Statistical Comparables
For a prospect, the three NBA players whose statistical role and style most
resemble theirs — purely descriptive resemblance, never a projection.

## Why DraftLens

- **Every score traces to a statistic.** No opaque ratings. Formulas are
  documented, unit-tested, and readable in [`src/features/`](src/features/).
- **Validated forwards through time.** Seven expanding-window folds — train
  on earlier drafts, predict a later unseen one. Random splitting is
  prohibited, because it would leak.
- **Leakage was hunted, not assumed.** Multiple channels were found and
  closed — including two where a feature leaked through its *availability*
  rather than its values. Date of birth is 100% present for drafted
  prospects and 69% for undrafted ones, so it's excluded, and so is any
  indicator that could reconstruct it.
- **The 2026 draft has never been opened.** It is a sealed holdout. No 2026
  target has been loaded and no 2026 prediction generated, and tests enforce
  this structurally, not by convention.
- **Nothing is faked when the data is absent.** There is no athleticism
  measurement in the data, so DraftLens does not score athleticism — and
  refuses a request for it rather than quietly substituting dunk rate.
- **NBA comparables describe, they don't predict.** They're generated without
  the system ever seeing who a historical prospect became.
- **Negative results are published.** Draft Order's numeric predicted pick is
  accurate to only ±13 picks on a 60-pick draft — not display-safe, so only
  its ordering is ever used. That limitation is in `docs/VALIDATION.md`, not
  hidden.

---

## Current status

| Component | Status |
| --- | --- |
| Historical data pipeline (2011–2026, 4 public sources) | ✅ implemented |
| Identity resolution + leakage audit | ✅ implemented |
| Basketball feature engineering | ✅ implemented |
| **General Draft Board** (Draft Probability + Draft Order + Overall Score) | ✅ frozen |
| **Team Need** | ✅ frozen |
| **NBA Statistical Comparables** | ✅ frozen |
| Web application | 🚧 not started |

**There is no application yet** — this repository is the analytical core. All
three product systems are frozen and reproducible on historical classes; the
2026 holdout is sealed until the designated replay phase.

### Where it currently stands, honestly

| | Result | Reading |
| --- | --- | --- |
| Draft Probability | macro ROC-AUC **0.6986** | Real signal; still close to a transparent percentile baseline (0.6943) |
| Draft Order | macro Spearman **0.2968** | Orders drafted prospects better than any baseline, but modestly |
| General Board | binary AUC **0.7123**, graded NDCG **0.8283** | Beats either signal alone; Draft Order's incremental value is real but modest |
| Draft Order exact pick | MAE **13.3 picks** | **Not display-safe** — the ordering is useful, the number is not |
| Team Need | no ground truth exists | Not a prediction — validated for consistency, stability and transparency instead |
| NBA comparables | no ground truth exists | Descriptive resemblance only; the third name is often one of several equally close |

Pre-draft NCAA box-score data explains a real but limited share of draft
outcomes. Workouts, medicals, interviews and team need are not in this data
and never will be. `docs/VALIDATION.md` says so in detail.

---

## Repository

```
src/
  data/         acquisition, identity resolution, dataset build
  features/     basketball formulas + feature engineering
  board/        Draft Probability, Draft Order, General Board
  team_need/    six-dimension peer-percentile fit scoring
  comparables/  NBA statistical comparables
  validation.py leakage rules, temporal protocol, shared guards
  paths.py      filesystem locations

scripts/
  acquire.py    fetch raw public data
  build.py      dataset -> features -> team_need/comparables references
  validate.py   run every domain's validator
  demo.py       exercise the three product APIs on one historical class

config/         board.json · team_need.json · comparables.json
tests/          data/ · features/ · board/ · team_need/ · comparables/ · integration/
docs/           DATA.md · METHODOLOGY.md · VALIDATION.md
data/           raw (immutable, git-ignored) / interim (generated, git-ignored)
```

## Run locally

```bash
pip install -e .

python scripts/acquire.py mbb --years 2011-2026        # ~200 MB, not committed
python scripts/acquire.py nba --years 2011-2026
python scripts/acquire.py population --years 2011-2026 --wikidata

python scripts/build.py            # dataset -> features -> team_need -> comparables
python scripts/validate.py         # every domain's validator
python scripts/demo.py --year 2024 # General Board + Team Need + Comparables on one class

python -m unittest discover -s tests -t .
```

Acquisition is the only slow step and is not needed to read the results —
`docs/VALIDATION.md` is self-contained. Generated analytical outputs are
git-ignored; every published number is regenerated by the commands above and
checked against tight tolerances by `tests/integration/test_frozen_anchors.py`.

**Sources**, all public and openly licensed: hoopR/ESPN college and NBA
basketball (CC BY 4.0), English Wikipedia draft articles (CC BY-SA 4.0),
Wikidata (CC0 1.0).

---

## Documentation

| Document | What it covers |
| --- | --- |
| [docs/DATA.md](docs/DATA.md) | Sources, licensing, population, identity resolution, source hazards |
| [docs/METHODOLOGY.md](docs/METHODOLOGY.md) | The final system: how each of the three products works and why |
| [docs/VALIDATION.md](docs/VALIDATION.md) | The evidence — fold results, leakage findings, stability audits, honest limitations |

Working conventions for this repository are in [CLAUDE.md](CLAUDE.md).
