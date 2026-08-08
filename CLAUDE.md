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

## Repository layout

```
docs/        product, data, ML, architecture, and decision documents
data/        raw (immutable) / interim / processed — see data/README.md
notebooks/   exploratory analysis
scripts/     reproducible data and analysis scripts
tests/       tests
```
