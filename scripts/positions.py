"""Deterministic, leakage-safe position handling (ML-1).

ML-1 established that the ONLY leakage-safe pre-draft position source is
hoopR's `hoopr_position`, which is coarse: G / F / C (plus ATH / NA).

`position_from_population` (the Wikipedia label) must NOT be used: drafted
prospects inherit it from the DRAFT RESULTS table (fine PG/SG/SF/PF/C labels)
while undrafted prospects inherit it from the early-entrant list (broad G/F).
Measured on 2014-2025, it resolves to a five-position label for 100% of drafted
versus 7.7% of undrafted — the label's granularity encodes the outcome. It is
on the ML-0 deny list (DEC-065).

Consequence: the PG/SG/SF/PF/C product scheme (DEC-009) has NO leakage-safe
source today. `parse_five_position` is retained as a correct, tested parser for
whenever such a source is obtained; it is deliberately NOT applied to
`position_from_population`.

Nothing here reads draft outcome, pick, NBA position or statistics.
"""

import csv
from pathlib import Path

CONFIG = Path(__file__).resolve().parents[1] / "config" / "position_map.csv"
UNKNOWN = "UNKNOWN"

# hoopR label -> canonical coarse position. Leakage-safe: the vocabulary and
# availability are near-identical for drafted and undrafted prospects.
HOOPR_TO_3 = {
    "G": "G", "PG": "G", "SG": "G",
    "F": "F", "SF": "F", "PF": "F",
    "C": "C",
    "ATH": UNKNOWN, "NA": UNKNOWN, "": UNKNOWN,
}

_MAP = None


def load_map(path=CONFIG):
    out = {}
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[r["raw_label"].strip().upper()] = (r["position_5"].strip(),
                                                   r["position_3"].strip())
    return out


def _table():
    global _MAP
    if _MAP is None:
        _MAP = load_map()
    return _MAP


def normalize_label(raw):
    """Uppercase, strip whitespace, unify separators. Lookup key only — the raw
    value is always preserved by the caller."""
    if raw is None:
        return ""
    s = str(raw).strip().upper().replace("\\", "/").replace("-", "/")
    s = s.replace(" ", "")
    return "" if s in ("", "NAN", "NA", "NONE") else s


def to_position_3(hoopr_label):
    """Canonical coarse position (G/F/C) from hoopR. THE leakage-safe path."""
    return HOOPR_TO_3.get(normalize_label(hoopr_label), UNKNOWN)


def parse_five_position(raw):
    """Deterministic PG/SG/SF/PF/C parse of a position label.

    Rules: an explicit five-position label maps to itself; a composite takes the
    FIRST listed position; a broad label (G, F, G/F, F/C) is UNKNOWN because
    resolving PG vs SG or SF vs PF would require inference.

    NOT currently applied to any DraftLens field — see the module docstring.
    """
    return _table().get(normalize_label(raw), (UNKNOWN, UNKNOWN))[0]
