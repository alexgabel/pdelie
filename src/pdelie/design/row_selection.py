"""v0.35c: deterministic row selection for design matrices.

Three methods pick ``k`` rows from a design matrix. All are pure NumPy, contain
no RNG, and are core-installable -- ``pdelie.design`` imports neither scipy nor
pysindy.

Why the QR is hand-rolled
=========================

Column-pivoted QR is the natural primitive here, and ``numpy.linalg.qr`` does not
provide it: its signature is ``(a, mode)`` with no ``pivoting`` parameter.
``scipy.linalg.qr(pivoting=True)`` does, but scipy is **not** a core dependency
of this package (core is ``numpy>=2,<3``; scipy appears only in the
``[downstream]`` and ``[test]`` extras) and no core module imports it. Making
``pdelie.design`` the first would break the core-only install that the
``package-smoke`` and ``py314-core-only-advisory`` CI jobs verify.

So :func:`qr_pivot_row_selection` implements Householder QR with column pivoting
directly (Golub & Van Loan, *Matrix Computations*, 4th ed., Algorithm 5.4.1).
SciPy is retained as a **test-side reference oracle**, where it is already
available.

What agreement with the oracle can and cannot mean
--------------------------------------------------

The pivot sequence is only *determined* where the competing column norms are
separated by more than rounding. Measured across the eight canonical matrices,
four are determined (minimum relative gap between the best and runner-up norm at
every step: Hilbert(7) 6.7e-02, graded-scale 9.8e-01, wide 3.0e-02, weak-form
8.9e-02) and four are not (identity, orthonormal, rank-deficient, tied-norm --
gaps of 0 or 1.1e-16).

On the undetermined four **every tie-break is equally valid, and SciPy's own
choice is not portable**: on the orthonormal matrix it pivots ``[1 0 2 3]`` under
one LAPACK and ``[0 1 2 3]`` under another. So the contract is split:

* on matrices where pivoting has strict signal, the permutation is **identical**
  to ``scipy.linalg.qr(pivoting=True)``;
* on every matrix, determined or not, the **selection quality** matches -- the
  resulting condition number and the magnitudes of the R diagonal agree with the
  oracle, which is the property that actually matters;
* our own output is **deterministic** in all cases, which SciPy's is not across
  platforms.

Two implementation details are contracts, not accidents
-------------------------------------------------------

**Tie-break.** Pivot on the largest remaining column norm; on an exact tie the
*lowest column index* wins. ``np.argmax`` returns the first maximal index, which
is that rule. This is *our* contract and is asserted directly against a
deliberately tied matrix -- deliberately not against SciPy, whose tie-break
varies by platform.

**Norm-downdate safeguard.** Trailing column norms are downdated incrementally
and recomputed from scratch when a downdated value falls below ``1e-8`` times its
original -- the LINPACK safeguard against catastrophic cancellation. This was
measured to be load-bearing, not defensive boilerplate: across twelve
adversarial matrices (Kahan, high-order Hilbert, near-dependent blocks) the
safeguard changed the permutation in **eight**, and in every one of those the
guarded result matched the SciPy oracle while the unguarded result did not.

The Kahan matrix is the extreme case of the same effect: built specifically to
defeat column pivoting, with *every* column norm exactly 1.0, it agrees with the
oracle through order 28 and diverges at 30 and above -- while the resulting
condition number stays identical (1.4008e+05 at order 30). Divergence there is a
tie broken differently, not a worse selection.

Choosing between the methods
============================

:func:`qr_pivot_row_selection` and :func:`d_optimal_exchange_row_selection` both
target conditioning and, measured against 40 random draws per matrix, beat
**100%** of them. :func:`leverage_row_selection` answers a different question --
which rows individually carry the most influence -- and is **not** a conditioning
method: on the canonical weak matrix it beat only **8%** of random draws
(condition number 2.52e+05 against a random median of 4.52e+04). It is offered
because high-leverage rows are worth *knowing about*, not because dropping to
them improves a fit.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np

from pdelie.errors import ScopeValidationError, ShapeValidationError

__all__ = [
    "NORM_RECOMPUTE_RATIO",
    "ROW_SELECTION_METHODS",
    "d_optimal_exchange_row_selection",
    "leverage_row_selection",
    "pivoted_qr_permutation",
    "qr_pivot_row_selection",
    "summarize_row_selection",
]

#: Recompute a trailing column norm from scratch once its incrementally
#: downdated value falls below this fraction of its original.
NORM_RECOMPUTE_RATIO = 1e-8

#: Frozen method vocabulary.
ROW_SELECTION_METHODS = ("qr_pivot", "d_optimal_exchange", "leverage")

_DEFAULT_MAX_EXCHANGE_ITERATIONS = 100


def _validated_matrix(design_matrix: object) -> np.ndarray:
    values = np.asarray(design_matrix, dtype=float)
    if values.ndim != 2:
        raise ShapeValidationError(
            f"design_matrix must be two-dimensional (rows, features); got shape "
            f"{values.shape}."
        )
    if values.size == 0:
        raise ScopeValidationError("design_matrix must contain at least one entry.")
    if not np.all(np.isfinite(values)):
        raise ScopeValidationError("design_matrix must be finite everywhere.")
    return values


def _validated_count(num_rows_to_select: object, n_rows: int) -> int:
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


def pivoted_qr_permutation(matrix: object) -> tuple[np.ndarray, int]:
    """Householder QR with column pivoting (Golub & Van Loan Algorithm 5.4.1).

    Returns ``(column_permutation, norm_recompute_count)``. The permutation is
    the order in which columns were pivoted; the count reports how often the
    cancellation safeguard fired, so a caller can see that it did.
    """
    working = np.array(_validated_matrix(matrix), dtype=float, copy=True)
    n_rows, n_columns = working.shape
    permutation = np.arange(n_columns)

    squared_norms = (working * working).sum(axis=0)
    original_norms = squared_norms.copy()
    recompute_count = 0

    for step in range(min(n_rows, n_columns)):
        # np.argmax returns the FIRST maximal index, which is the frozen
        # lowest-index tie-break.
        pivot = int(np.argmax(squared_norms[step:])) + step
        if pivot != step:
            working[:, [step, pivot]] = working[:, [pivot, step]]
            permutation[[step, pivot]] = permutation[[pivot, step]]
            squared_norms[[step, pivot]] = squared_norms[[pivot, step]]
            original_norms[[step, pivot]] = original_norms[[pivot, step]]

        if squared_norms[step] <= 0.0:
            break

        column = working[step:, step]
        column_norm = float(np.linalg.norm(column))
        if column_norm == 0.0:  # pragma: no cover - guarded by the check above
            continue

        # Sign chosen to avoid cancellation in the leading reflector entry.
        alpha = -column_norm if column[0] >= 0.0 else column_norm
        reflector = column.copy()
        reflector[0] -= alpha
        reflector_norm = float(np.linalg.norm(reflector))
        if reflector_norm > 0.0:
            reflector = reflector / reflector_norm
            working[step:, step:] -= 2.0 * np.outer(
                reflector, reflector @ working[step:, step:]
            )

        for column_index in range(step + 1, n_columns):
            squared_norms[column_index] -= working[step, column_index] ** 2
            if (
                squared_norms[column_index]
                < NORM_RECOMPUTE_RATIO * original_norms[column_index]
            ):
                exact = float((working[step + 1 :, column_index] ** 2).sum())
                squared_norms[column_index] = exact
                original_norms[column_index] = exact
                recompute_count += 1
        squared_norms[step] = 0.0

    return permutation, recompute_count


def _selection_report(
    *,
    method: str,
    selected: list[int],
    values: np.ndarray,
    warnings_out: list[str],
    extra: dict[str, Any],
) -> dict[str, Any]:
    block = values[selected]
    singular_values = np.linalg.svd(block, compute_uv=False)
    largest = float(singular_values[0]) if singular_values.size else 0.0
    smallest = float(singular_values[-1]) if singular_values.size else 0.0
    condition_number = float(largest / smallest) if smallest > 0.0 else None
    if condition_number is None:
        warnings_out.append("selected_rows_are_rank_deficient")

    report: dict[str, Any] = {
        "metric_name": "row_selection",
        "method": method,
        "selected_row_indices": list(selected),
        "num_rows_selected": len(selected),
        "num_rows_available": int(values.shape[0]),
        "num_features": int(values.shape[1]),
        "selected_condition_number": condition_number,
        "selected_matrix_rank": int(np.linalg.matrix_rank(block)),
        "direction": "lower_condition_number_is_better",
        "warnings": warnings_out,
        "diagnostic_only": True,
    }
    report.update(extra)
    return report


def _fewer_rows_than_features_warning(
    values: np.ndarray, count: int, warnings_out: list[str]
) -> None:
    if count < values.shape[1]:
        warnings_out.append("selected_fewer_rows_than_features")


def qr_pivot_row_selection(
    design_matrix: object, num_rows_to_select: object
) -> dict[str, Any]:
    """Select rows by column-pivoted QR on the transpose.

    Pivoting the columns of ``A.T`` is pivoting the rows of ``A``: the first
    ``k`` pivots name the rows that span the row space best. Fully deterministic.
    """
    values = _validated_matrix(design_matrix)
    count = _validated_count(num_rows_to_select, values.shape[0])

    permutation, recompute_count = pivoted_qr_permutation(values.T)
    selected = sorted(int(index) for index in permutation[:count])

    warnings_out: list[str] = []
    _fewer_rows_than_features_warning(values, count, warnings_out)

    return _selection_report(
        method="qr_pivot",
        selected=selected,
        values=values,
        warnings_out=warnings_out,
        extra={
            "norm_recompute_count": recompute_count,
            "tie_break_policy": "largest_remaining_column_norm_then_lowest_index",
            "interpretation": (
                "Rows chosen by Householder QR with column pivoting on the "
                "transpose. Deterministic; targets conditioning."
            ),
        },
    )


def leverage_row_selection(
    design_matrix: object, num_rows_to_select: object
) -> dict[str, Any]:
    """Select the ``k`` highest-leverage rows.

    **Not a conditioning method.** Measured on the canonical weak-form matrix,
    this selection beat only 8% of 40 random draws on condition number, against
    100% for the other two. High-leverage rows are the rows a fit is most
    sensitive to, which is worth knowing; restricting a fit to them is a
    different and usually worse idea.
    """
    values = _validated_matrix(design_matrix)
    count = _validated_count(num_rows_to_select, values.shape[0])

    left_vectors, singular_values, _ = np.linalg.svd(values, full_matrices=False)
    tolerance = (
        max(values.shape) * float(np.finfo(float).eps) * float(singular_values[0])
    )
    rank = int((singular_values > tolerance).sum())
    scores = (left_vectors[:, :rank] ** 2).sum(axis=1)

    # Descending score, ascending index on ties -- deterministic.
    order = sorted(range(len(scores)), key=lambda index: (-scores[index], index))
    selected = sorted(order[:count])

    warnings_out: list[str] = ["leverage_selection_does_not_target_conditioning"]
    _fewer_rows_than_features_warning(values, count, warnings_out)

    return _selection_report(
        method="leverage",
        selected=selected,
        values=values,
        warnings_out=warnings_out,
        extra={
            "selected_leverage_scores": [float(scores[index]) for index in selected],
            "tie_break_policy": "descending_leverage_then_lowest_index",
            "interpretation": (
                "Rows with the highest statistical leverage. Reports influence, "
                "not conditioning; see the method warning."
            ),
        },
    )


def d_optimal_exchange_row_selection(
    design_matrix: object,
    num_rows_to_select: object,
    *,
    initial_rows: object = None,
    max_iterations: int = _DEFAULT_MAX_EXCHANGE_ITERATIONS,
) -> dict[str, Any]:
    """Fedorov-style exchange maximizing ``log det(A_S^T A_S)``.

    The exchange contains no RNG and is repeat-stable, but it is a local search:
    measured across three matrices and five random starting sets, it reached
    **four to five distinct optima** depending only on where it began. The
    starting set is therefore part of the contract. It defaults to the
    deterministic :func:`qr_pivot_row_selection` result rather than a random
    subset, and the resolved start is reported so a result can be reproduced.

    Note that maximizing the determinant is not the same as minimizing the
    condition number, and the two can disagree: measured on a 200x5 matrix the
    exchange improved the determinant while leaving a slightly worse condition
    number (2.499) than its QR starting point (2.384).
    """
    values = _validated_matrix(design_matrix)
    count = _validated_count(num_rows_to_select, values.shape[0])
    if not isinstance(max_iterations, (int, np.integer)) or isinstance(
        max_iterations, bool
    ):
        raise ScopeValidationError("max_iterations must be an integer.")
    if int(max_iterations) < 1:
        raise ScopeValidationError("max_iterations must be at least 1.")

    if initial_rows is None:
        start = list(qr_pivot_row_selection(values, count)["selected_row_indices"])
        start_source = "qr_pivot"
    else:
        if isinstance(initial_rows, (str, bytes)) or not isinstance(
            initial_rows, Iterable
        ):
            raise ScopeValidationError(
                "initial_rows must be an iterable of integer row indices."
            )
        try:
            start = sorted({int(index) for index in initial_rows})
        except (TypeError, ValueError) as exc:
            raise ScopeValidationError(
                "initial_rows must be an iterable of integer row indices."
            ) from exc
        if len(start) != count:
            raise ScopeValidationError(
                f"initial_rows must name exactly {count} distinct rows; got "
                f"{len(start)}."
            )
        if any(not 0 <= index < values.shape[0] for index in start):
            raise ScopeValidationError(
                "initial_rows contains an index outside the available rows."
            )
        start_source = "caller_supplied"

    def log_determinant(rows: list[int]) -> float:
        sign, value = np.linalg.slogdet(values[rows].T @ values[rows])
        return float(value) if sign > 0 else float("-inf")

    current = list(start)
    best = log_determinant(current)
    iterations = 0
    converged = False
    for iterations in range(1, int(max_iterations) + 1):
        improved = False
        for position in range(count):
            for candidate in range(values.shape[0]):
                if candidate in current:
                    continue
                trial = list(current)
                trial[position] = candidate
                value = log_determinant(trial)
                # Strict improvement only: an exact tie keeps the incumbent, so
                # the search cannot cycle between equal-value swaps.
                if value > best + 1e-12:
                    best, current, improved = value, trial, True
        if not improved:
            iterations -= 1
            converged = True
            break

    selected = sorted(current)
    warnings_out: list[str] = []
    _fewer_rows_than_features_warning(values, count, warnings_out)
    if not converged:
        warnings_out.append("d_optimal_exchange_hit_max_iterations")

    return _selection_report(
        method="d_optimal_exchange",
        selected=selected,
        values=values,
        warnings_out=warnings_out,
        extra={
            "initial_row_indices": list(start),
            "initial_rows_source": start_source,
            "exchange_iterations": int(iterations),
            "converged": converged,
            "log_determinant": best if np.isfinite(best) else None,
            "tie_break_policy": "strict_improvement_only_incumbent_wins_ties",
            "interpretation": (
                "Local exchange search maximizing log det(A_S^T A_S). "
                "Deterministic given a starting set; the result depends on it."
            ),
        },
    )


def summarize_row_selection(
    design_matrix: object, num_rows_to_select: object
) -> dict[str, Any]:
    """Run all three methods and report them side by side."""
    values = _validated_matrix(design_matrix)
    count = _validated_count(num_rows_to_select, values.shape[0])

    qr_report = qr_pivot_row_selection(values, count)
    exchange_report = d_optimal_exchange_row_selection(values, count)
    leverage_report = leverage_row_selection(values, count)

    aggregated: list[str] = []
    for block in (qr_report, exchange_report, leverage_report):
        for warning in block["warnings"]:
            if warning not in aggregated:
                aggregated.append(warning)

    return {
        "summary_type": "pdelie_row_selection_diagnostic",
        "num_rows_available": int(values.shape[0]),
        "num_features": int(values.shape[1]),
        "num_rows_selected": count,
        "methods": list(ROW_SELECTION_METHODS),
        "qr_pivot": qr_report,
        "d_optimal_exchange": exchange_report,
        "leverage": leverage_report,
        "warnings": aggregated,
        "diagnostic_only": True,
    }
