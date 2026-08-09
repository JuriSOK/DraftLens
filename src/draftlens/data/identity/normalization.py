"""Name and school normalisation for cross-source joins.

DraftLens joins Wikipedia (population and draft results) to hoopR (statistics)
on names alone — there is no shared identifier. Three distinct keys exist and
they are NOT interchangeable:

  normalize_name  canonical identity, written once into the raw population CSVs.
                  Frozen: changing it would invalidate every canonical_prospect_id.
  match_key       matching-only key with two documented corrections over
                  normalize_name. Never persisted as identity.
  norm_school     school/program key used to disambiguate same-name players.

Nothing here reads a draft outcome.
"""

import re
import unicodedata

SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}

# Characters NFKD cannot decompose into ASCII + combining marks.
_TRANSLITERATIONS = (("ø", "o"), ("æ", "ae"), ("å", "a"), ("ß", "ss"),
                     ("ł", "l"), ("đ", "d"), ("ð", "d"), ("þ", "th"), ("ı", "i"))


def normalize_name(s):
    """Casefold, strip accents/suffixes/punctuation. The CANONICAL identity key.

    Known quirk, deliberately not fixed: the suffix rule strips "v" anywhere in
    the string, so "V. J. Edgecombe" loses its leading initial. `match_key`
    compensates for matching purposes. Correcting it here would change every
    `canonical_prospect_id` already written to disk (DEC-063).
    """
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b\.?", "", s)
    return re.sub(r"\s+", " ", re.sub(r"[^a-z ]", "", s)).strip()


def match_key(s):
    """Matching-only name key. Never replaces `normalized_name`.

    Two deterministic corrections over normalize_name, both general rules and
    not player-specific:
      1. Suffixes are stripped ONLY at the end, so a leading initial "V." is
         preserved rather than removed as a Roman numeral.
      2. Leading single-letter tokens are merged: Wikipedia writes "T. J. Warren",
         ESPN writes "TJ Warren".
    """
    s = str(s).lower()
    for a, b in _TRANSLITERATIONS:
        s = s.replace(a, b)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    toks = re.sub(r"[^a-z ]", "", s).split()
    while toks and toks[-1] in SUFFIXES:
        toks.pop()
    lead, i = [], 0
    while i < len(toks) - 1 and len(toks[i]) == 1:
        lead.append(toks[i])
        i += 1
    if lead:
        toks = ["".join(lead)] + toks[i:]
    return " ".join(toks)


def norm_school(s):
    """School key. Program suffixes are stripped BEFORE apostrophes, otherwise
    "Saint Mary's men's basketball" loses the wrong substring."""
    if not isinstance(s, str):
        return ""
    s = s.lower().replace("’", "'")
    for junk in (" men's basketball", " basketball"):
        s = s.replace(junk, "")
    s = s.replace("&", " and ").replace("'", "")
    s = s.replace("st.", "state").replace("–", "-").replace("—", "-")
    return " ".join(s.split())
