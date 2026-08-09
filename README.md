# DraftLens

**A data-driven NBA Draft decision-support tool for scouting departments — built on transparent pre-draft analytics, validated the way a draft actually happens: forwards through time.**

Built for the **AQX Sports Analytics Data Bowl 3.0**.

---

## The problem

Draft evaluation leans on subjective judgment and public consensus boards that are hard to audit. A scouting department cannot interrogate a mock draft: it cannot ask *why* a prospect ranks where they do, or which measurements moved them.

DraftLens answers a narrower, checkable question:

> Among declared NCAA early entrants, using **only** information available before a given draft, which prospects does the objective record support — and how highly?

## Two ranking modes

**General Draft Board** — overall prospect quality, from a two-stage model:
- **Stage A** — the probability a prospect is drafted at all.
- **Stage B** — among drafted prospects, how highly their profile suggests they go.

**Team Need** — a separate, deterministic ranking against the traits a team is actually looking for. Six basketball archetypes plus a custom weighted mode, scored as percentiles against the full NCAA population. It is *not* a re-weighting of the board: across historical classes the two rankings correlate at only ρ = 0.18–0.62, and each archetype surfaces different players.

## What makes it different

- **Every score traces to a statistic.** No opaque ratings. Formulas are documented, unit-tested, and readable in [`src/draftlens/features/`](src/draftlens/features/).
- **Validated forwards through time.** Seven expanding-window folds — train on earlier drafts, predict a later unseen one. Random splitting is prohibited, because it would leak.
- **Leakage was hunted, not assumed.** Three separate channels were found and closed, including two where a feature leaked through its *availability* rather than its values. Date of birth is 100% present for drafted prospects and 69% for undrafted ones — so it is excluded, and so is any indicator that could reconstruct it.
- **The 2026 draft has never been opened.** It is a sealed holdout. No 2026 target has been loaded and no 2026 prediction generated, and tests enforce this.
- **Negative results are published.** Tree ensembles beat the linear model on the headline metric — until a fold with two negative examples was removed, at which point the winner fell from 1st to 12th. It is in the report.
- **Nothing is faked when the data is absent.** There is no athleticism measurement in the data, so DraftLens does not score athleticism — and rejects a request for it rather than quietly substituting dunk rate.

---

## Current status

| Component | Status |
| --- | --- |
| Historical data pipeline (2011–2026, 3 public sources) | ✅ implemented |
| Identity resolution + leakage audit | ✅ implemented |
| Basketball feature engineering | ✅ implemented |
| **Stage A** — P(drafted) | ✅ frozen |
| **Stage B** — draft ranking | ✅ frozen |
| **General Draft Board + Overall Score /100** | ✅ frozen |
| **Team Need analytics** | ✅ frozen |
| NBA statistical comparables | 🚧 not started |
| Web application | 🚧 not started |

**There is no application yet** — this repository is the analytical core. Both ranking modes are frozen and reproducible on historical classes, but no NBA comparable and no user interface exists today.

### Where it currently stands, honestly

| | Result | Reading |
| --- | --- | --- |
| Stage A | macro ROC-AUC **0.6986** | Real signal; still close to a transparent percentile baseline (0.6943) |
| Stage B | macro Spearman **0.2968** | Orders drafted prospects better than any baseline, but modestly |
| General Board | binary AUC **0.7123**, graded NDCG **0.8283** | Beats both stages alone; Stage B's incremental value is real but modest |
| Stage B exact pick | MAE **13.3 picks** | **Not display-safe** — the ordering is useful, the number is not |
| Team Need | no ground truth exists | Not a prediction — validated for consistency, stability and transparency instead |

Pre-draft NCAA box-score data explains a real but limited share of draft outcomes. Workouts, medicals, interviews and team need are not in this data and never will be. The reports say so.

---

## Reproducibility

```bash
pip install -e .

python scripts/build_dataset.py        # ML-0 prospect dataset (population gates)
python scripts/build_features.py       # basketball feature layer
python scripts/run_stage_a.py          # backtest frozen Stage A
python scripts/run_stage_b.py          # backtest frozen Stage B
python scripts/validate.py             # leakage + population + determinism
python -m unittest discover -s tests -t .
```

Raw data (~200 MB) is **not committed** but is fully reproducible:

```bash
python scripts/acquire_data.py --source mbb --years 2011-2026
python scripts/acquire_data.py --source population --years 2011-2026
```

Acquisition is the only slow step and is not needed to read the results — the reports in [`docs/experiments/`](docs/experiments/) are self-contained. Generated analytical outputs are git-ignored; every published number is regenerated by the commands above and checked against tight tolerances by `tests/integration/test_frozen_anchors.py`.

**Sources**, all public and openly licensed: hoopR/ESPN college basketball (CC BY 4.0), English Wikipedia draft articles (CC BY-SA 4.0), Wikidata (CC0 1.0).

---

## Documentation

| Document | What it covers |
| --- | --- |
| [docs/PRODUCT.md](docs/PRODUCT.md) | Product definition — the source of truth for behaviour |
| [docs/MVP.md](docs/MVP.md) | MVP scope |
| [docs/DATA.md](docs/DATA.md) | Source audit, licensing, verified data hazards |
| [docs/ML_SPEC.md](docs/ML_SPEC.md) | Methodology, leakage rules, validation protocol |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | How the code is organised and how data flows |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Every durable decision, with evidence |
| [docs/experiments/](docs/experiments/) | Frozen phase reports — the analytical record |

**Start here if you are reviewing:** [ARCHITECTURE.md](docs/ARCHITECTURE.md) for the shape of the system, then [ML4_STAGE_A.md](docs/experiments/ML4_STAGE_A.md) §9 for the most interesting result in the project.

Working conventions for this repository are in [CLAUDE.md](CLAUDE.md).
