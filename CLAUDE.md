# CLAUDE.md — Working instructions for DraftLens

DraftLens is a data-driven NBA Draft decision-support tool built for the AQX
Sports Analytics Data Bowl 3.0. **The analytical methodology is frozen.**
Three product systems — General Draft Board, Team Need, NBA Statistical
Comparables — are implemented, tested and validated on historical data. No
web application exists yet. The 2026 draft remains a sealed holdout until an
explicit replay phase.

## Before you change anything

1. **Read [docs/METHODOLOGY.md](docs/METHODOLOGY.md) before touching any
   analytical behavior.** It is the authoritative record of what each system
   does and why each choice was made.
2. **Read [docs/DATA.md](docs/DATA.md) before touching data acquisition,
   identity resolution, or feature engineering.** It records verified source
   hazards that cost real effort to find.
3. **Read [docs/VALIDATION.md](docs/VALIDATION.md) before citing a
   metric.** It is the evidence backing every number in this repository.
4. **Never silently modify a frozen decision.** If one appears wrong or
   infeasible, say so and ask — do not work around it.

## Honesty about facts

5. **Never fabricate** datasets, statistics, model results, benchmark
   results, or sources.
6. **Clearly distinguish** verified facts, assumptions, and TBD decisions in
   everything you write — code, comments, docs, and replies.
7. **Stop and mark something TBD rather than inventing** an important
   product, data, or analytical decision. An explicit TBD is a correct
   answer; a plausible-looking invention is not.

## Analytical integrity

8. **Never introduce future-information leakage into historical validation.**
   This includes feature construction, normalization statistics, imputation
   fits, and hyperparameter selection — not just the training split.
9. **Historical analysis must only use information available before the
   evaluated draft.**
10. **Do not use external analyst rankings as model features** — ESPN, The
    Athletic, mock drafts, consensus boards. They may be used only as
    external benchmarks, and only after an explicit product decision.
11. **Missing data must not be silently fabricated.** Imputation is allowed
    only through an explicitly documented and approved method. A dimension
    with no data source (e.g. Team Need's Athleticism) stays `UNAVAILABLE`
    forever — it is never proxied.

## Data handling

12. **Preserve raw data as immutable.** Never edit anything in `data/raw/`
    in place.
13. **Derived datasets belong in `data/interim/`.**
14. **Keep data transformations reproducible** — scripted, re-runnable, and
    documented.

## Implementation discipline

15. **Do not add a dependency or choose a new technology without discussing
    it first.** The current dependency set (`pandas`, `pyarrow`, `numpy`,
    `scipy`, `scikit-learn`) is deliberately minimal.
16. **Prefer simple, justified implementations over unnecessary complexity.**
    Do not add a feature unless it materially improves scouting usefulness,
    analytical credibility, explainability, or hackathon presentation.
17. **Run the relevant tests after meaningful changes**
    (`python -m unittest discover -s tests -t .`), and `scripts/validate.py`
    after anything touching data, features, or a product system.
18. **Update `docs/METHODOLOGY.md` or `docs/VALIDATION.md` when an
    implementation changes an approved contract.**

## Code architecture

19. **Reusable analytical logic belongs under `src/`** — `data/`,
    `features/`, `board/`, `team_need/`, `comparables/`, plus the top-level
    `validation.py` and `paths.py`. `scripts/` holds four thin CLI entry
    points only: `acquire.py`, `build.py`, `validate.py`, `demo.py` — parse
    arguments, call the library, print, return an exit code.
20. **Never duplicate a formula in a script.** If a script needs a
    calculation, the calculation belongs in `src/` and the script imports it.
    Two implementations of one formula is a defect, not redundancy.
21. **Read the relevant module before changing analytical behaviour.** The
    docstrings record *why* a constraint exists — most of them encode a
    leakage finding that cost real effort to discover.
22. **Name modules for what they do, not when they were written.**
    `probability.py`, not `stage_a.py`; `board/`, not `ml/`. The product does
    not know what "Stage A" or "ML-6" means, and neither should new code.
    Git history is the chronological record — the working tree represents
    the current system only.

## Frozen state — do not change without an explicit decision

23. **Draft Probability, Draft Order and the General Board method are
    FROZEN.** The selections live in `board.probability.DRAFT_PROBABILITY`,
    `board.order.DRAFT_ORDER`, and `board.scoring.GENERAL_BOARD`
    (documented in `docs/METHODOLOGY.md` §2). Changing a model,
    hyperparameter, feature set, representation or combination method is a
    *scientific* change requiring its own evaluation phase — never a
    refactor or a drive-by edit.
24. **Team Need's six dimensions and NBA Comparables' six-dimension common
    space are FROZEN** (`docs/METHODOLOGY.md` §3–4). Neither has a ground
    truth to optimize against; nothing about them may be tuned to make a
    specific prospect "look right."
25. **The published anchors are asserted by
    `tests/integration/test_frozen_anchors.py`.** If one fails, find out what
    changed. Do not loosen a tolerance to make it pass.
26. **2026 is a sealed holdout.** Do not load its targets, generate
    predictions for it, or inspect its picks until the designated replay
    phase.

## Repository layout

```
src/
  data/          acquisition, identity resolution, dataset build
  features/      basketball formulas + feature engineering
  board/         Draft Probability, Draft Order, General Board
  team_need/     six-dimension peer-percentile fit scoring
  comparables/   NBA statistical comparables
  validation.py  leakage rules, temporal protocol, shared guards
  paths.py       filesystem locations
scripts/         acquire.py · build.py · validate.py · demo.py — nothing else
config/          board.json · team_need.json · comparables.json
docs/            DATA.md · METHODOLOGY.md · VALIDATION.md — nothing else
data/            raw (immutable, git-ignored) / interim (generated, git-ignored)
tests/           data/ · features/ · board/ · team_need/ · comparables/ · integration/
```

Keep it this shape. A new top-level module under `src/` or a new file under
`scripts/` needs a real, cohesive reason — not "it seemed easier to add a
file than to extend an existing one."
