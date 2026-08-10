"""Canonical filesystem locations.

One definition, so no module has to guess how many parent directories it sits
below the repository root.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DATA = ROOT / "data"
RAW = DATA / "raw"
INTERIM = DATA / "interim"
PROCESSED = DATA / "processed"

CONFIG = ROOT / "config"

DOCS = ROOT / "docs"
MANIFEST = DATA / "source_manifest.csv"

# hoopR men's college basketball corpus
MBB = RAW / "hoopr_mbb"


def interim(phase):
    """Generated-artifact directory for a pipeline phase. Always git-ignored."""
    p = INTERIM / phase
    p.mkdir(parents=True, exist_ok=True)
    return p


def rel(path):
    """Repository-relative path string, for manifests and logs."""
    return str(Path(path).resolve().relative_to(ROOT))
