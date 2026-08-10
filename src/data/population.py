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


def load_declared(year):
    """The ORIGINAL declared NCAA pool for `year` (before withdrawal), if a
    snapshot was acquired (`scripts/acquire.py declared`). Returns None — not
    an empty frame — when no snapshot exists, so callers can distinguish "no
    withdrawals occurred" from "not yet acquired". PRODUCT/DISPLAY use only;
    never an ML sampling frame (see `load_population`)."""
    path = POP_DIR / f"draft_declared_{year}.csv"
    if not path.exists():
        return None
    declared = pd.read_csv(path)
    declared["draft_year"] = year
    declared["canonical_prospect_id"] = (
        declared.draft_year.astype(str) + "-"
        + declared.normalized_name.str.replace(" ", "_"))
    return declared.reset_index(drop=True)


FINAL_ENTRY = "FINAL_ENTRY"
WITHDRAWN = "WITHDRAWN"


def population_status(year):
    """Eligibility/process status for every prospect on the declared pool:
    FINAL_ENTRY (remained through the withdrawal deadline — the approved ML
    sampling frame) or WITHDRAWN (declared, then withdrew before the draft).

    Uses ONLY declaration/withdrawal facts — never a draft outcome. Returns
    None if no declared-pool snapshot has been acquired for `year`.
    """
    declared = load_declared(year)
    if declared is None:
        return None
    final = load_population(year)
    final_names = set(final.normalized_name)
    missing = final_names - set(declared.normalized_name)
    if missing:
        raise AssertionError(
            f"{year}: {len(missing)} final entrant(s) absent from the "
            f"declared-pool snapshot — investigate name matching: {missing}")
    out = declared[["canonical_prospect_id", "normalized_name", "player_name",
                    "college", "position", "class"]].copy()
    out["population_status"] = out.normalized_name.map(
        lambda n: FINAL_ENTRY if n in final_names else WITHDRAWN)
    return out.reset_index(drop=True)


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
