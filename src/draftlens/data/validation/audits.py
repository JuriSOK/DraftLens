"""Audits run whenever the prospect dataset is rebuilt.

These are gates, not reports: a denied column or a temporal mismatch fails the
build rather than printing a warning. The point is that a leak cannot be
introduced by an ordinary code change and merged unnoticed.
"""

from draftlens.leakage import (DENY_EXACT, DENY_SUBSTRING, SUSPICIOUS,
                               SUSPICIOUS_ALLOWED)


def leakage_audit(feats, label, report):
    """Columns that must never have been written, plus a review list.

    SUSPICIOUS is deliberately noisy — it flags anything name-matching "draft",
    "pick", "rank" etc. so a new column has to be consciously reviewed rather
    than slipping in because it looked harmless.
    """
    cols = list(feats.columns)
    hard = [c for c in cols if c.lower() in DENY_EXACT
            or any(s in c.lower() for s in DENY_SUBSTRING)]
    susp = [c for c in cols
            if any(s in c.lower() for s in SUSPICIOUS) and c not in SUSPICIOUS_ALLOWED
            and c not in hard]
    report[label] = dict(n_columns=len(cols), denied=hard,
                         suspicious_for_review=susp)
    return hard


def temporal_audit(feats, years, label, report):
    """Every row's NCAA season must equal its draft year, and no draft year may
    fall outside the partition window."""
    bad = feats[feats.ncaa_season.notna()
                & (feats.ncaa_season != feats.draft_year)]
    off_window = sorted(set(feats.draft_year) - set(years))
    report[label] = dict(rows=len(feats),
                         season_mismatch_rows=int(len(bad)),
                         draft_years=sorted(map(int, feats.draft_year.unique())),
                         unexpected_years=off_window)
    return len(bad) == 0 and not off_window


def missingness(feats, cols):
    out = {}
    for c in cols:
        if c not in feats.columns:
            continue
        n_missing = int(feats[c].isna().sum())
        out[c] = dict(missing=n_missing,
                      missing_pct=round(100 * n_missing / max(1, len(feats)), 2))
    return out


def coverage_by_outcome(feats, tgt, cols):
    """2014-2025 ONLY. Detects missingness that correlates with the target.

    A column whose AVAILABILITY differs between drafted and undrafted prospects
    is a leakage channel regardless of its values — this is how the DOB and
    position-label leaks were both found.
    """
    m = feats.merge(tgt[["canonical_prospect_id", "drafted"]],
                    on="canonical_prospect_id", how="inner")
    out = {}
    for c in cols:
        if c not in m.columns:
            continue
        d = 100 * m.loc[m.drafted == 1, c].notna().mean()
        u = 100 * m.loc[m.drafted == 0, c].notna().mean()
        out[c] = dict(drafted_coverage_pct=round(float(d), 2),
                      undrafted_coverage_pct=round(float(u), 2),
                      gap_pp=round(float(d - u), 2))
    return out
