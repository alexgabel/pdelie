"""v0.35a: report-only design-matrix diagnostics.

These describe whether a design matrix is *capable* of supporting sparse
recovery. They do not decide that a fit succeeded, and they make no claim about
noise robustness or dataset recovery.

Submodule-only, per the v0.35 scope: nothing here is exported from the root
``pdelie`` namespace.
"""

from __future__ import annotations

from pdelie.diagnostics.design_matrix import (
    COLUMN_SCALING_CONVENTION,
    RESTRICTED_EIGENVALUE_DEFINITION,
    irrepresentability_constant,
    leverage_scores,
    mutual_coherence,
    restricted_eigenvalue,
    summarize_design_matrix_diagnostics,
)

__all__ = [
    "COLUMN_SCALING_CONVENTION",
    "RESTRICTED_EIGENVALUE_DEFINITION",
    "irrepresentability_constant",
    "leverage_scores",
    "mutual_coherence",
    "restricted_eigenvalue",
    "summarize_design_matrix_diagnostics",
]
