# CLAUDE.md — Working instructions for DraftLens

DraftLens is a data-driven NBA Draft decision-support tool built for the AQX Sports Analytics Data Bowl 3.0. The repository is currently in a **documentation and bootstrap** phase — no application code exists, and no technology has been chosen.

## Before you change anything

1. **Read [docs/PRODUCT.md](docs/PRODUCT.md) before making any product-related change.** It is the authoritative source of truth for product behavior.
2. **Read the relevant specification document before implementing a feature** — [docs/DATA.md](docs/DATA.md), [docs/ML_SPEC.md](docs/ML_SPEC.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/MVP.md](docs/MVP.md).
3. **Never silently modify an approved product decision.** If a decision appears wrong or infeasible, say so and ask — do not work around it.
4. **Record meaningful new decisions in [docs/DECISIONS.md](docs/DECISIONS.md).** Supersede prior entries rather than editing them away.

## Honesty about facts

5. **Never fabricate** datasets, statistics, model results, benchmark results, or sources.
6. **Clearly distinguish** verified facts, assumptions, and TBD decisions in everything you write — code, comments, docs, and replies.
7. **Stop and mark something TBD rather than inventing** an important product, data, or ML decision. An explicit TBD is a correct answer; a plausible-looking invention is not.

## Analytical integrity

8. **Never introduce future-information leakage into historical validation.** This includes feature construction, normalization statistics, imputation fits, and hyperparameter selection — not just the training split.
9. **Historical analysis must only use information available before the evaluated draft.**
10. **Do not use external analyst rankings as model features** — ESPN, The Athletic, mock drafts, consensus boards — unless PRODUCT.md is explicitly changed first. They may be used only as external benchmarks.
11. **Missing data must not be silently fabricated.** Imputation is allowed only through an explicitly documented and approved method.

## Data handling

12. **Preserve raw data as immutable.** Never edit anything in `data/raw/` in place.
13. **Derived datasets belong in `data/interim/` or `data/processed/`.**
14. **Keep data transformations reproducible** — scripted, re-runnable, and documented.

## Implementation discipline

15. **Do not install dependencies or choose technologies before architecture decisions are approved.** See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
16. **Prefer simple, justified implementations over unnecessary complexity.** Do not add a feature unless it materially improves scouting usefulness, analytical credibility, explainability, or hackathon presentation.
17. **Once implementation begins, run the relevant tests after meaningful changes.**
18. **Update documentation when an implementation changes an approved contract.**

## Code architecture

19. **Reusable analytical logic belongs in `src/draftlens/`.** `scripts/` holds thin CLI entry points: parse arguments, call the library, print, return an exit code.
20. **Never duplicate a formula in a script.** If a script needs a calculation, the calculation belongs in the package and the script imports it. Two implementations of one formula is a defect, not redundancy.
21. **Read the relevant module before changing analytical behaviour.** The docstrings record *why* a constraint exists — most of them encode a leakage finding that cost real effort to discover.
22. **Name library modules for what they do, not when they were written.** `stage_a.py`, not `ml4_common.py`. Experiment scripts and phase reports keep their phase names, because there the chronology is the point.

## Frozen state — do not change without an explicit decision

23. **Stage A and Stage B are FROZEN.** The selections live in `draftlens.ml.stage_a.STAGE_A` and `draftlens.ml.stage_b.STAGE_B` (DEC-080…091). Changing a model, hyperparameter, feature set, representation or target is a *scientific* change requiring its own evaluation phase and a DECISIONS entry — never a refactor or a drive-by edit.
24. **The published anchors are asserted by `tests/integration/test_frozen_anchors.py`.** If one fails, find out what changed. Do not loosen a tolerance to make it pass.
25. **2026 is a sealed holdout.** Do not load its targets, generate predictions for it, or inspect its picks until the designated holdout phase.
26. **Experiment scripts under `scripts/experiments/` are historical evidence.** Keep them runnable; do not use them to change a frozen selection.

## Repository layout

```
src/draftlens/   reusable analytical library (data / features / ml)
scripts/         thin CLI entry points; experiments/ holds historical runs
config/          data/ · features/ · ml/ — versioned configuration
docs/            specs; experiments/ holds frozen phase reports
data/            raw (immutable) / interim / processed — see data/README.md
tests/           data/ · features/ · ml/ · integration/
notebooks/       exploratory analysis
```
