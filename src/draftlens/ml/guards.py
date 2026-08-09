"""Reusable assertions shared by every phase validator.

Six phase validators previously repeated the same holdout / population /
deny-list / chronology checks. Consolidating them here means a guard is
strengthened once and every phase benefits — and that a phase cannot
accidentally ship a weaker version of a check that already exists.

Phase-specific rules stay in their own validator; only the universal ones live
here.
"""

import subprocess

import pandas as pd

from draftlens.leakage import DENIED, DENIED_SUBSTR, denied_columns
from draftlens.ml.validation import HOLDOUT_YEAR, folds
from draftlens.paths import ROOT

# Frozen analytical anchors. These are the numbers the reports publish; if a
# refactor or a data refresh moves them, the science changed and the phase
# result must be re-derived rather than the tolerance loosened.
DEVELOPMENT_POPULATION = (887, 431, 456)      # rows, drafted, undrafted
STAGE_B_POPULATION = 431
UNRESOLVED_PROSPECTS = 8                       # all undrafted (DEC-071)


class Guard:
    """Collects failures instead of raising, so one run reports every problem."""

    def __init__(self):
        self.failures, self.warnings = [], []

    def check(self, cond, msg, hard=True):
        if cond:
            return True
        (self.failures if hard else self.warnings).append(msg)
        print(f"  {'FAIL' if hard else 'WARN'}  {msg}")
        return False

    def report(self):
        print(f"\n{'=' * 78}\nRESULT\n{'=' * 78}")
        print(f"  hard failures: {len(self.failures)}\n"
              f"  warnings     : {len(self.warnings)}")
        for m in self.failures:
            print(f"   FAIL {m}")
        for m in self.warnings:
            print(f"   WARN {m}")
        return 1 if self.failures else 0


# ------------------------------------------------------------------ guards
def check_holdout_absent(g, frames, where=""):
    """`frames`: {label: dataframe-or-iterable-of-years}."""
    for label, obj in frames.items():
        if isinstance(obj, pd.DataFrame):
            for col in ("draft_year", "validate_year"):
                if col in obj.columns:
                    vals = set(pd.to_numeric(obj[col], errors="coerce").dropna())
                    g.check(HOLDOUT_YEAR not in vals,
                            f"{label}: {HOLDOUT_YEAR} present in {col} {where}")
        else:
            g.check(HOLDOUT_YEAR not in set(obj),
                    f"{label}: {HOLDOUT_YEAR} present {where}")


def check_artifacts_holdout_free(g, out_dir):
    """No generated artifact may contain a holdout row, in any year column."""
    for p in sorted(out_dir.glob("*")):
        if p.suffix not in (".csv", ".parquet"):
            continue
        df = pd.read_csv(p, index_col=0) if p.suffix == ".csv" \
            else pd.read_parquet(p)
        for col in df.columns:
            if any(k in str(col).lower() for k in ("year", "season")):
                vals = pd.to_numeric(df[col], errors="coerce").dropna()
                g.check(HOLDOUT_YEAR not in set(vals),
                        f"{p.name}: {HOLDOUT_YEAR} in column {col}")


def check_source_never_loads_holdout(g, *paths):
    for path in paths:
        src = path.read_text()
        for banned in ("targets_2026", "features_2026", "predictions_2026"):
            g.check(banned not in src, f"{path.name} references {banned}")


def check_development_population(g, dev):
    n, nd, nu = len(dev), int(dev.drafted.sum()), int((dev.drafted == 0).sum())
    expected = DEVELOPMENT_POPULATION
    g.check((n, nd, nu) == expected,
            f"development population is {(n, nd, nu)}, expected {expected}")
    unresolved = int(dev.hoopr_athlete_id.isna().sum())
    g.check(unresolved >= UNRESOLVED_PROSPECTS,
            f"unresolved prospects lost ({unresolved} < {UNRESOLVED_PROSPECTS})")
    return unresolved


def check_features_safe(g, columns, where=""):
    bad = denied_columns(columns)
    g.check(not bad, f"denied features entered X{' (' + where + ')' if where else ''}: {bad}")


def check_fitted_model_clean(g, coef_index, extra_denied=frozenset()):
    """Compare on the BARE column name.

    DENIED holds exact names; substring-matching it would flag legitimate
    features such as `usage_pct`, which contains "age". Only DENIED_SUBSTR is a
    substring rule.
    """
    bare = [str(i).split("__", 1)[-1] for i in coef_index]
    bad = [n for n in bare if n in DENIED or n in extra_denied
           or any(s in n.lower() for s in DENIED_SUBSTR)]
    g.check(not bad, f"denied/target field in the fitted model: {bad}")


def check_chronology(g, cfg=None):
    for fold, tr, vy in folds(cfg):
        g.check(max(tr) < vy, f"fold {fold}: a training year is not before {vy}")


def check_fold_coverage(g, fold_df, cfg=None):
    expected = {vy for _, _, vy in folds(cfg)}
    for name, grp in fold_df.groupby("config"):
        g.check(set(grp.validate_year) == expected,
                f"{name}: folds {sorted(set(grp.validate_year))} != "
                f"{sorted(expected)}")


def check_predictions_complete(g, oof, population, key="draft_year"):
    """Every eligible row must have received a prediction — no complete-case
    deletion anywhere in the pipeline."""
    for name, grp in oof.groupby("config"):
        for vy, gg in grp.groupby(key):
            expect = int((population.draft_year == vy).sum())
            g.check(len(gg) == expect,
                    f"{name} {vy}: {len(gg)} predictions for {expect} prospects "
                    f"— rows were dropped")


def check_artifacts_untracked(g, rel_dir):
    tracked = subprocess.run(["git", "ls-files", rel_dir],
                             capture_output=True, text=True, cwd=ROOT)
    g.check(not tracked.stdout.strip(),
            f"generated artifacts are tracked by Git: "
            f"{tracked.stdout.split()[:5]}")


def check_reruns_identically(g, script, out_file, before, sort_by):
    """Re-execute a pipeline and require every metric to match."""
    import sys
    rerun = subprocess.run([sys.executable, str(script)],
                           capture_output=True, text=True, cwd=ROOT)
    if not g.check(rerun.returncode == 0,
                   f"{script.name} is not re-runnable:\n{rerun.stderr[-2000:]}"):
        return
    after = pd.read_csv(out_file)
    a = before.sort_values(sort_by).reset_index(drop=True).round(6)
    b = after.sort_values(sort_by).reset_index(drop=True).round(6)
    g.check(a.equals(b),
            "a second run produced different results — the selection cannot "
            "be reproduced")
