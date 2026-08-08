# Archived feasibility-audit scripts

One-off scripts that produced the evidence in `docs/DATA.md` §22 (hoopR
small-sample verification) and §23 (Wikidata DOB feasibility audit). They are
kept as reproducible evidence for those findings, **not** as production code.

| Script | Produced | Superseded by |
| --- | --- | --- |
| `verify_hoopr_sample.py` | §22 schema/fill-rate audit of four 2026 files | `scripts/validate_raw_data.py` |
| `verify_hoopr_sample2.py` | §22 corrected ID/shot-type/prospect-match checks | `scripts/validate_raw_data.py` |
| `audit_wikidata_dob.py` | §23 DOB coverage, precision and cross-check | `scripts/acquire_draft_population.py --wikidata` |

They expect the pre-consolidation raw layout (`data/raw/hoopR-mbb-data/…`) and
will not run against the current `data/raw/hoopr_mbb/…` structure without edits.
Use the maintained scripts in `scripts/` for anything ongoing.
