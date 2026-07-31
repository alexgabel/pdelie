"""v0.35c: deterministic row selection for design matrices.

Report-only. These functions choose rows; they do not decide that a fit built on
those rows is correct, and they make no noise-robustness claim.

Pure NumPy and core-installable: nothing here imports scipy or pysindy.
Submodule-only, per the v0.35 scope -- nothing is exported from the root
``pdelie`` namespace.
"""

from __future__ import annotations

from pdelie.design.attainability import (
    ATTAINABILITY_SUMMARY_TYPE,
    attainability_report,
    budgets_are_equal,
)
from pdelie.design.budget import BUDGET_UNITS, DUPLICATE_POLICIES, DesignBudget
from pdelie.design.candidate_record import (
    MANDATORY_ACCESS_KEYS,
    METHOD_CLASSES,
    DesignCandidateRecord,
    validate_information_access,
)
from pdelie.design.comparators import (
    COMPARATOR_NAMES,
    EXACT_ENUMERATION_MAX_ROWS,
    d_optimal_exchange_comparator,
    exact_enumeration_comparator,
    full_field_design,
    leverage_score_selection_comparator,
    qr_pivot_selection_comparator,
    random_budget_matched_design,
    raw_local_design,
    translation_orbit_design,
)
from pdelie.design.lineage import (
    DesignRowLineage,
    compute_numeric_design_hash,
    compute_semantic_design_hash,
)
from pdelie.design.row_selection import (
    NORM_RECOMPUTE_RATIO,
    ROW_SELECTION_METHODS,
    d_optimal_exchange_row_selection,
    leverage_row_selection,
    pivoted_qr_permutation,
    qr_pivot_row_selection,
    summarize_row_selection,
)
from pdelie.design.statistics import paired_bootstrap_interval

__all__ = [
    "ATTAINABILITY_SUMMARY_TYPE",
    "BUDGET_UNITS",
    "COMPARATOR_NAMES",
    "DUPLICATE_POLICIES",
    "EXACT_ENUMERATION_MAX_ROWS",
    "MANDATORY_ACCESS_KEYS",
    "METHOD_CLASSES",
    "NORM_RECOMPUTE_RATIO",
    "ROW_SELECTION_METHODS",
    "DesignBudget",
    "DesignCandidateRecord",
    "DesignRowLineage",
    "attainability_report",
    "budgets_are_equal",
    "compute_numeric_design_hash",
    "compute_semantic_design_hash",
    "d_optimal_exchange_comparator",
    "d_optimal_exchange_row_selection",
    "exact_enumeration_comparator",
    "full_field_design",
    "leverage_row_selection",
    "leverage_score_selection_comparator",
    "paired_bootstrap_interval",
    "pivoted_qr_permutation",
    "qr_pivot_row_selection",
    "qr_pivot_selection_comparator",
    "random_budget_matched_design",
    "raw_local_design",
    "summarize_row_selection",
    "translation_orbit_design",
    "validate_information_access",
]
