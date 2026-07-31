"""v0.36c: the eight design comparators.

Each produces a :class:`~pdelie.design.candidate_record.DesignCandidateRecord`
declaring its method class and all six information-access flags.

Three of these wrap v0.35c rather than reimplementing it
=======================================================

:func:`qr_pivot_selection_comparator`,
:func:`leverage_score_selection_comparator`, and
:func:`d_optimal_exchange_comparator` delegate to
:mod:`pdelie.design.row_selection`. That is deliberate. Reimplementing would
fork two things that were measured into their current shape:

* the **lowest-index tie-break** on equal column norms, which is what makes the
  pivoted QR reproducible at all;
* the **LINPACK norm-downdate safeguard**, measured load-bearing on **8 of 12**
  adversarial matrices -- without it the permutation diverges from the SciPy
  reference on high-order Hilbert and near-dependent designs.

Two v0.35c measurements also shape the declarations below rather than being
rediscovered here:

* ``leverage_row_selection`` beat only **8%** of 40 random draws on the
  canonical weak matrix, where the other two beat 100%. It is an influence
  diagnostic, not a conditioning method, and its record says so.
* ``d_optimal_exchange_row_selection`` reached **4-5 distinct optima** across
  five random starts. Its seed and starting set are part of its identity, so
  both are recorded.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Sequence
from typing import Any

import numpy as np

from pdelie.design.budget import DesignBudget
from pdelie.design.candidate_record import DesignCandidateRecord
from pdelie.design.row_selection import (
    d_optimal_exchange_row_selection,
    leverage_row_selection,
    qr_pivot_row_selection,
)
from pdelie.errors import ScopeValidationError, ShapeValidationError

__all__ = [
    "COMPARATOR_NAMES",
    "EXACT_ENUMERATION_MAX_ROWS",
    "EXACT_ENUMERATION_MAX_SUBSETS",
    "d_optimal_exchange_comparator",
    "exact_enumeration_comparator",
    "full_field_design",
    "leverage_score_selection_comparator",
    "qr_pivot_selection_comparator",
    "random_budget_matched_design",
    "raw_local_design",
    "translation_orbit_design",
]

#: Above this row count, exact enumeration is refused and ``None`` is returned.
#:
#: The cap is on ``n_rows`` but the *cost* is ``C(n, k)``, maximal at ``k = n/2``.
#: ``n <= 20`` bounds it at ``C(20, 10) = 184,756`` subsets, measured at **3.6 s**
#: at roughly 51,578 subsets/second. At ``n = 22`` the same worst case is
#: ``705,432`` subsets -- about 14 s -- which is past the point where a
#: diagnostic should silently spend the caller's time.
EXACT_ENUMERATION_MAX_ROWS = 20

#: The subset count the row cap actually bounds. Reported so the reason for the
#: cap is legible from the payload rather than only from this docstring.
EXACT_ENUMERATION_MAX_SUBSETS = math.comb(EXACT_ENUMERATION_MAX_ROWS, EXACT_ENUMERATION_MAX_ROWS // 2)

COMPARATOR_NAMES: tuple[str, ...] = (
    "raw_local_design",
    "random_budget_matched_design",
    "translation_orbit_design",
    "leverage_score_selection_comparator",
    "qr_pivot_selection_comparator",
    "d_optimal_exchange_comparator",
    "full_field_design",
    "exact_enumeration_comparator",
)

#: The common case: a method that uses only what a practitioner has at design
#: time. Individual comparators override the flags they actually need.
_NO_PRIVILEGED_ACCESS: dict[str, bool] = {
    "uses_true_support": False,
    "uses_true_coefficients": False,
    "requires_full_domain": False,
    "requires_unobserved_rows": False,
    "requires_heldout_data": False,
    "uses_future_time": False,
}


def _access(**overrides: bool) -> dict[str, bool]:
    access = dict(_NO_PRIVILEGED_ACCESS)
    access.update(overrides)
    return access


def _validated(design_matrix: object) -> np.ndarray:
    values = np.asarray(design_matrix, dtype=float)
    if values.ndim != 2:
        raise ShapeValidationError(
            f"design_matrix must be two-dimensional; got shape {values.shape}."
        )
    if values.size == 0:
        raise ScopeValidationError("design_matrix must contain at least one entry.")
    if not np.all(np.isfinite(values)):
        raise ScopeValidationError("design_matrix must be finite everywhere.")
    return values


def _count(num_rows_to_select: object, n_rows: int) -> int:
    if isinstance(num_rows_to_select, bool) or not isinstance(
        num_rows_to_select, (int, np.integer)
    ):
        raise ScopeValidationError("num_rows_to_select must be an integer.")
    count = int(num_rows_to_select)
    if not 1 <= count <= n_rows:
        raise ScopeValidationError(
            f"num_rows_to_select must lie in [1, {n_rows}]; got {count}."
        )
    return count


def _condition_number(matrix: np.ndarray, rows: Sequence[int]) -> float | None:
    block = matrix[list(rows)]
    singular = np.linalg.svd(block, compute_uv=False)
    if singular.size == 0 or singular[-1] <= 0.0:
        return None
    value = float(singular[0] / singular[-1])
    return value if math.isfinite(value) else None


def _record(
    *,
    design_id: str,
    method_name: str,
    method_class: str,
    rows: Sequence[int],
    matrix: np.ndarray,
    budget: DesignBudget,
    access: dict[str, bool],
    seed: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> DesignCandidateRecord:
    ordered = tuple(sorted(int(index) for index in rows))
    return DesignCandidateRecord(
        design_id=design_id,
        method_name=method_name,
        method_class=method_class,
        selected_row_indices=ordered,
        budget=budget,
        information_access=access,
        selected_condition_number=_condition_number(matrix, ordered),
        seed=seed,
        metadata=metadata or {},
    )


def raw_local_design(
    design_matrix: object, num_rows_to_select: object, *, budget: DesignBudget, design_id: str = "raw_local"
) -> DesignCandidateRecord:
    """The first ``k`` rows, in order. The do-nothing baseline."""
    matrix = _validated(design_matrix)
    count = _count(num_rows_to_select, matrix.shape[0])
    return _record(
        design_id=design_id,
        method_name="raw_local_design",
        method_class="attainable_policy",
        rows=range(count),
        matrix=matrix,
        budget=budget,
        access=_access(),
        metadata={"interpretation": "first k rows in order; the do-nothing baseline"},
    )


def random_budget_matched_design(
    design_matrix: object,
    num_rows_to_select: object,
    *,
    budget: DesignBudget,
    seed: int,
    design_id: str = "random_budget_matched",
) -> DesignCandidateRecord:
    """A uniform random subset of the same size. Seeded, so it reproduces."""
    matrix = _validated(design_matrix)
    count = _count(num_rows_to_select, matrix.shape[0])
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ScopeValidationError("seed must be an integer; a baseline must reproduce.")
    generator = np.random.default_rng(seed)
    rows = generator.choice(matrix.shape[0], size=count, replace=False)
    return _record(
        design_id=design_id,
        method_name="random_budget_matched_design",
        method_class="attainable_policy",
        rows=rows.tolist(),
        matrix=matrix,
        budget=budget,
        access=_access(),
        seed=seed,
        metadata={"interpretation": "uniform random subset at the same budget"},
    )


def translation_orbit_design(
    design_matrix: object,
    num_rows_to_select: object,
    *,
    budget: DesignBudget,
    shifts: Sequence[int],
    design_id: str = "translation_orbit",
) -> DesignCandidateRecord:
    """Rows sampled along a translation orbit, at integer grid shifts.

    Integer shifts are exact on a periodic grid -- the v0.34b measurement rests
    on the same property -- so the orbit carries no interpolation error.
    """
    matrix = _validated(design_matrix)
    count = _count(num_rows_to_select, matrix.shape[0])
    if isinstance(shifts, (str, bytes)) or not isinstance(shifts, Sequence) or not shifts:
        raise ScopeValidationError("shifts must be a non-empty sequence of integers.")
    offsets = [int(value) for value in shifts]
    rows: list[int] = []
    start = 0
    while len(rows) < count:
        for offset in offsets:
            candidate = (start + offset) % matrix.shape[0]
            if candidate not in rows:
                rows.append(candidate)
            if len(rows) == count:
                break
        start += 1
    return _record(
        design_id=design_id,
        method_name="translation_orbit_design",
        method_class="attainable_policy",
        rows=rows,
        matrix=matrix,
        budget=budget,
        access=_access(),
        metadata={"shifts": offsets, "interpretation": "rows along a translation orbit"},
    )


def leverage_score_selection_comparator(
    design_matrix: object,
    num_rows_to_select: object,
    *,
    budget: DesignBudget,
    design_id: str = "leverage_selection",
) -> DesignCandidateRecord:
    """Highest-leverage rows. **Not a conditioning method.**

    Wraps v0.35c. Declares ``requires_unobserved_rows=True``: leverage is
    computed from the full design matrix, including rows a practitioner would
    not have measured yet.

    Measured in v0.35c: this beat only **8%** of 40 random draws on the
    canonical weak matrix, where qr_pivot and d_optimal each beat 100%. The
    record carries that so a reader does not mistake it for a conditioning
    baseline.
    """
    matrix = _validated(design_matrix)
    count = _count(num_rows_to_select, matrix.shape[0])
    report = leverage_row_selection(matrix, count)
    return _record(
        design_id=design_id,
        method_name="leverage_score_selection_comparator",
        method_class="full_design_matrix_heuristic",
        rows=report["selected_row_indices"],
        matrix=matrix,
        budget=budget,
        access=_access(requires_unobserved_rows=True, requires_full_domain=True),
        metadata={
            "wraps": "pdelie.design.row_selection.leverage_row_selection",
            "targets_conditioning": False,
            "measured_v0_35c_random_draws_beaten_percent": 8,
            "interpretation": "reports row influence, not conditioning",
            "tie_break_policy": report["tie_break_policy"],
        },
    )


def qr_pivot_selection_comparator(
    design_matrix: object,
    num_rows_to_select: object,
    *,
    budget: DesignBudget,
    design_id: str = "qr_pivot",
) -> DesignCandidateRecord:
    """Column-pivoted QR on the transpose. Wraps v0.35c, deterministic."""
    matrix = _validated(design_matrix)
    count = _count(num_rows_to_select, matrix.shape[0])
    report = qr_pivot_row_selection(matrix, count)
    return _record(
        design_id=design_id,
        method_name="qr_pivot_selection_comparator",
        method_class="full_design_matrix_heuristic",
        rows=report["selected_row_indices"],
        matrix=matrix,
        budget=budget,
        access=_access(requires_unobserved_rows=True, requires_full_domain=True),
        metadata={
            "wraps": "pdelie.design.row_selection.qr_pivot_row_selection",
            "targets_conditioning": True,
            "tie_break_policy": report["tie_break_policy"],
            "norm_recompute_count": report["norm_recompute_count"],
        },
    )


def d_optimal_exchange_comparator(
    design_matrix: object,
    num_rows_to_select: object,
    *,
    budget: DesignBudget,
    seed: int | None = None,
    max_iterations: int = 100,
    design_id: str = "d_optimal_exchange",
) -> DesignCandidateRecord:
    """Fedorov exchange maximizing log-det. Wraps v0.35c.

    Measured in v0.35c: **4-5 distinct optima** across five random starting
    sets. The start is therefore part of the identity. With ``seed=None`` the
    deterministic QR selection seeds the search; with an integer the start is a
    seeded random subset, and both the seed and the resolved start are recorded.
    """
    matrix = _validated(design_matrix)
    count = _count(num_rows_to_select, matrix.shape[0])

    initial_rows = None
    if seed is not None:
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ScopeValidationError("seed must be an int or None.")
        generator = np.random.default_rng(seed)
        initial_rows = sorted(
            generator.choice(matrix.shape[0], size=count, replace=False).tolist()
        )

    report = d_optimal_exchange_row_selection(
        matrix, count, initial_rows=initial_rows, max_iterations=max_iterations
    )
    return _record(
        design_id=design_id,
        method_name="d_optimal_exchange_comparator",
        method_class="full_design_matrix_heuristic",
        rows=report["selected_row_indices"],
        matrix=matrix,
        budget=budget,
        access=_access(requires_unobserved_rows=True, requires_full_domain=True),
        seed=seed,
        metadata={
            "wraps": "pdelie.design.row_selection.d_optimal_exchange_row_selection",
            "targets_conditioning": True,
            "is_local_search": True,
            "initial_row_indices": list(report["initial_row_indices"]),
            "initial_rows_source": report["initial_rows_source"],
            "converged": report["converged"],
            "exchange_iterations": report["exchange_iterations"],
            "measured_v0_35c_distinct_optima_across_five_starts": "4-5",
        },
    )


def full_field_design(
    design_matrix: object, *, budget: DesignBudget, design_id: str = "full_field"
) -> DesignCandidateRecord:
    """Every row. Uses the whole domain, which a practitioner may not have."""
    matrix = _validated(design_matrix)
    return _record(
        design_id=design_id,
        method_name="full_field_design",
        method_class="full_design_matrix_heuristic",
        rows=range(matrix.shape[0]),
        matrix=matrix,
        budget=budget,
        access=_access(requires_full_domain=True, requires_unobserved_rows=True),
        metadata={"interpretation": "every row; an upper reference, not a policy"},
    )


def exact_enumeration_comparator(
    design_matrix: object,
    num_rows_to_select: object,
    *,
    budget: DesignBudget,
    design_id: str = "exact_enumeration",
) -> DesignCandidateRecord | None:
    """The genuinely optimal subset by condition number, or ``None`` if too large.

    Returns ``None`` when ``n_rows > 20``. The cap is on rows but the cost is
    ``C(n, k)``: ``n <= 20`` bounds it at ``C(20, 10) = 184,756`` subsets,
    measured at 3.6 s. At ``n = 22`` the worst case is 705,432 subsets, roughly
    14 s, which a diagnostic should not spend without being asked.

    This is ``exact_small_problem_solver``, **not** an oracle: it uses no
    privileged information, only exhaustive search of a small space. Beating a
    heuristic here says the heuristic is suboptimal, not that it cheated.
    """
    matrix = _validated(design_matrix)
    count = _count(num_rows_to_select, matrix.shape[0])
    if matrix.shape[0] > EXACT_ENUMERATION_MAX_ROWS:
        return None

    best_rows: tuple[int, ...] | None = None
    best_condition = math.inf
    for combination in itertools.combinations(range(matrix.shape[0]), count):
        condition = _condition_number(matrix, combination)
        if condition is not None and condition < best_condition:
            best_condition, best_rows = condition, combination
    if best_rows is None:
        return None

    return _record(
        design_id=design_id,
        method_name="exact_enumeration_comparator",
        method_class="exact_small_problem_solver",
        rows=best_rows,
        matrix=matrix,
        budget=budget,
        access=_access(requires_full_domain=True, requires_unobserved_rows=True),
        metadata={
            "subsets_enumerated": math.comb(matrix.shape[0], count),
            "max_rows": EXACT_ENUMERATION_MAX_ROWS,
            "max_subsets_bounded_by_row_cap": EXACT_ENUMERATION_MAX_SUBSETS,
            "interpretation": (
                "exhaustive search of a small space; optimal by condition number, "
                "and uses no privileged information"
            ),
        },
    )
