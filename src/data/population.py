"""The DraftLens historical sampling frame.

The population is FINAL NCAA EARLY ENTRANTS ONLY.

Why not "every drafted NCAA player": automatically-eligible players (principally
seniors) appear on no pre-draft list, so they become identifiable only once they
are drafted. Including them would let post-draft information decide population
membership — a leak in the sampling frame that no feature engineering can undo.
Measured: under the earlier union rule, 212 of 212 non-early-entrants were
drafted, 100.0%.

Declared early entrants are published ~8 days before the draft, so membership is
genuinely pre-draft information.
"""

import pandas as pd

from paths import RAW

POP_DIR = RAW / "draft_population"
TGT_DIR = RAW / "draft_targets"

COVID_YEARS = {2021, 2022}

# (rows, drafted, undrafted) per partition — asserted whenever the dataset is
# rebuilt so a silent population change cannot pass unnoticed.
EXPECTED = {"2014_2025": (887, 431, 456), "2026": (26, None, None),
            "2011_2013": (125, 85, 40)}


def load_population(year):
    """Final NCAA early entrants only — the approved ML sampling frame."""
    pop = pd.read_csv(POP_DIR / f"draft_population_{year}.csv")
    pop = pop[pop.early_entrant.astype(str) == "True"].copy()
    pop["draft_year"] = year
    pop["canonical_prospect_id"] = (
        pop.draft_year.astype(str) + "-" + pop.normalized_name.str.replace(" ", "_"))
    return pop.reset_index(drop=True)


def load_targets(year, pop):
    """Draft outcome for the population. Read ONLY from data/raw/draft_targets/
    and never joined into a feature frame before the feature boundary."""
    tgt = pd.read_csv(TGT_DIR / f"draft_targets_{year}.csv")
    tgt = tgt[tgt.normalized_name.isin(set(pop.normalized_name))].copy()
    tgt["draft_year"] = year
    tgt["canonical_prospect_id"] = (
        tgt.draft_year.astype(str) + "-" + tgt.normalized_name.str.replace(" ", "_"))
    tgt["drafted"] = tgt.drafted.astype(str).eq("True").astype(int)
    tgt["pick"] = pd.to_numeric(tgt["pick"], errors="coerce").astype("Int64")
    tgt["round"] = pd.to_numeric(tgt["round"], errors="coerce").astype("Int64")
    return tgt[["canonical_prospect_id", "draft_year", "drafted", "pick", "round"]]
