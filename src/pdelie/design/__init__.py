"""v0.35c: deterministic row selection for design matrices.

Report-only. These functions choose rows; they do not decide that a fit built on
those rows is correct, and they make no noise-robustness claim.

Pure NumPy and core-installable: nothing here imports scipy or pysindy.
Submodule-only, per the v0.35 scope -- nothing is exported from the root
``pdelie`` namespace.
"""

from __future__ import annotations

from pdelie.design.row_selection import (
    NORM_RECOMPUTE_RATIO,
    ROW_SELECTION_METHODS,
    d_optimal_exchange_row_selection,
    leverage_row_selection,
    pivoted_qr_permutation,
    qr_pivot_row_selection,
    summarize_row_selection,
)

__all__ = [
    "NORM_RECOMPUTE_RATIO",
    "ROW_SELECTION_METHODS",
    "d_optimal_exchange_row_selection",
    "leverage_row_selection",
    "pivoted_qr_permutation",
    "qr_pivot_row_selection",
    "summarize_row_selection",
]
