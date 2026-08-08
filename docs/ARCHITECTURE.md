# DraftLens — Technical Architecture

**Status: NOT YET DEFINED**

> **Technical architecture will be selected only after MVP, data, and ML requirements are sufficiently defined.**

## Purpose of this document

This document will record the technical structure of DraftLens: how the application is built, how data flows through it, and how analysis is served to the user.

## Current state

Nothing has been chosen. In particular, **no decision has been made** on:

- frontend framework
- backend framework
- database
- hosting provider
- ML serving architecture
- visualization framework
- language(s), package manager, or build tooling
- testing framework
- containerization or deployment

No dependencies have been installed and no application code exists in this repository.

## Why this is deferred

Architecture is a consequence of requirements, not a prerequisite. Choosing a stack before knowing the MVP surface ([MVP.md](MVP.md)), the shape and volume of the data ([DATA.md](DATA.md)), and the computational demands of the methodology ([ML_SPEC.md](ML_SPEC.md)) would mean committing to constraints for no analytical gain.

## Constraints already known

Whatever is chosen must be compatible with the following, which are fixed by [PRODUCT.md](PRODUCT.md):

- **Reproducibility** — data processing and model evaluation should be reproducible wherever licensing allows.
- **Raw data visibility** — the interface must be able to display the factual statistics underlying every derived score.
- **Professional interface** — the product should look like an analytics / scouting tool, not a game.
- **No required generative AI dependency** — the MVP must not require a paid generative AI API.
- **Explainability** — explanations should preferably be generated deterministically from the scoring logic.
- **Immutable raw data** — the data directory convention in [../data/README.md](../data/README.md) must be respected.

## Next step

Architecture decisions will be made once [MVP.md](MVP.md), [DATA.md](DATA.md), and [ML_SPEC.md](ML_SPEC.md) are sufficiently defined. Each choice must be recorded in [DECISIONS.md](DECISIONS.md) with its rationale.
