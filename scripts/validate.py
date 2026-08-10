#!/usr/bin/env python3
"""Run DraftLens validation. Thin CLI over `validation.main`.

  python scripts/validate.py              # everything except raw checksums
  python scripts/validate.py --stage raw  # raw corpus + manifest integrity
"""

import argparse
import sys

import validation


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage", default="all", choices=["all", "raw"],
                    help="'raw' needs the full ~200 MB corpus on disk, so it "
                         "is opt-in")
    ap.add_argument("--skip-checksums", action="store_true",
                    help="raw stage only: skip SHA-256 verification (fast size check only)")
    a = ap.parse_args()

    if a.stage == "raw":
        from data.acquire import validate_raw
        return validate_raw(a.skip_checksums)

    return validation.main()


if __name__ == "__main__":
    sys.exit(main())
