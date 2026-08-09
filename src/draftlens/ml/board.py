"""General Draft Board — the combination of Stage A and Stage B.

NOT IMPLEMENTED. This module is the designated home for ML-6 and is empty on
purpose: inventing an API before the evidence exists is exactly what ML_SPEC 17
forbids.

What ML-6 has to decide, none of which may be assumed:
  * The Overall Score transformation, and whether it is class-relative or
    absolute (ML_SPEC 17.1 — still unresolved).
  * How a probability and an ordering combine, given that Stage A ships
    uncalibrated (DEC-083) and Stage B is an ordering rather than a magnitude
    (DEC-089).
  * Whether the board displays tiers, ranges, relative order or a score.

Binding constraints ML-6 inherits:
  * Order-preserving — if A ranks above B, A's score must be >= B's.
  * No false precision — a score must not imply a probability unless it is one.
  * Stage B carries less information than Stage A (macro Spearman 0.2968 vs
    Stage A macro ROC-AUC 0.6986), so a combination rule must not assume the
    two stages are equally informative.

The 2026 holdout remains sealed until ML-8. Nothing here may load it.
"""
