"""v0.35a: design-matrix diagnostics for sparse-regression identifiability.

Four report-only quantities that describe whether a design matrix is *capable*
of supporting sparse recovery. None of them decides that recovery succeeded --
they describe the matrix, not the fit.

Frozen contract, and why each choice was forced by measurement
==============================================================

**All four metrics are computed on the column-normalized matrix**
(``||a_j||_2 = 1``), never the raw one. This is not a style preference. Measured
on the canonical weak-form matrix, whose column norms span a factor of 1158:

===================  ================  ==================  ===================
metric               raw               column-normalized   arbitrary rescale
===================  ================  ==================  ===================
mutual coherence     0.9084512121      0.9084512121        0.9084512121
max leverage         0.9640848878      0.9640848878        0.9640848878
irrepresentability   1.129160013       2.742717168         **0.2955377896**
restricted eigenval  8.556977e-10      6.509027e-03        6.899429e-08
===================  ================  ==================  ===================

Coherence and leverage are scale-invariant. The other two are not -- and the
*verdict* moves with them: an arbitrary but perfectly legitimate column rescaling
takes the irrepresentability constant from 1.13 ("recovery not guaranteed") to
0.30 ("recovery guaranteed") on identical data. A diagnostic whose scientific
conclusion depends on an unstated scaling is worse than no diagnostic, so the
scaling is fixed here and reported in every payload.

``||a_j||_2 = 1`` is chosen over the ``||a_j||_2 = sqrt(n)`` convention also seen
in the literature because it is what the already-shipped v0.34c
:func:`~pdelie.discovery.column_normalize.column_normalize_design_matrix`
produces -- verified bit-identical to a hand-written normalization on the
canonical matrix. The two conventions differ by exactly a factor of ``n`` in
:func:`restricted_eigenvalue` (measured: 1.041444e-01 vs 6.509027e-03 at
``n = 16``); multiply by ``n`` to convert.

**Leverage is computed from the thin SVD, never from the hat matrix.** Forming
``A^T A`` squares the condition number. Measured against the analytic answer on
Hilbert matrices, where the square full-rank case gives leverage exactly 1.0
everywhere:

==============  ===========  =======================  ==================
matrix          cond(A)      hat-matrix route error   SVD route error
==============  ===========  =======================  ==================
Hilbert(5)      4.766e+05    1.387e-06                8.882e-16
Hilbert(8)      1.526e+10    **5.634e-01**            6.661e-16
Hilbert(10)     1.603e+13    **6.258e-01**            4.441e-16
==============  ===========  =======================  ==================

An error of 0.56 on a quantity bounded in ``[0, 1]`` is not lost precision, it is
a wrong answer. The SVD route holds at machine epsilon throughout.

Definitions are frozen and single-valued; nothing here auto-dispatches between
competing conventions.

* **Mutual coherence** -- ``max_{i != j} |<a_i, a_j>|`` over unit-norm columns.
  Zero for an orthonormal design, one when two columns are collinear.
* **Leverage** -- ``h_i = ||U_i,:||^2`` from the rank-truncated thin SVD. Sums to
  the rank; each entry lies in ``[0, 1]``.
* **Irrepresentability constant** (Zhao & Yu 2006; Wainwright 2009) --
  ``max_{j not in S} || (A_S^T A_S)^-1 A_S^T a_j ||_1``. Lasso support recovery
  is guaranteed when this is ``< 1``. Stated in the source literature for
  normalized designs, which is the convention adopted above.
* **Restricted eigenvalue** (Bickel, Ritov & Tsybakov 2009, Assumption RE) --
  reported here as the computable support-restricted form
  ``lambda_min(A_S^T A_S) / n``, **not** the full cone-constrained constant.
  The BRT constant minimizes over all supports of a given size *and* over a
  cone, which is combinatorial; this is the exact quantity for a *given*
  support, and is an upper bound on it. The report says so in
  ``restricted_eigenvalue_definition`` rather than leaving a reader to assume
  the stronger quantity.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any

import numpy as np

from pdelie.discovery.column_normalize import column_normalize_design_matrix
from pdelie.errors import ScopeValidationError, ShapeValidationError

__all__ = [
    "COLUMN_SCALING_CONVENTION",
    "RESTRICTED_EIGENVALUE_DEFINITION",
    "irrepresentability_constant",
    "leverage_scores",
    "mutual_coherence",
    "restricted_eigenvalue",
    "summarize_design_matrix_diagnostics",
]

#: The single column scaling every metric in this module is computed under.
COLUMN_SCALING_CONVENTION = "unit_l2_column_norm"

#: Names the exact quantity reported, so a reader cannot mistake it for the
#: full cone-constrained Bickel-Ritov-Tsybakov constant.
RESTRICTED_EIGENVALUE_DEFINITION = "support_restricted_min_gram_eigenvalue_over_n"


def _validated_matrix(design_matrix: object, *, name: str = "design_matrix") -> np.ndarray:
    values = np.asarray(design_matrix, dtype=float)
    if values.ndim != 2:
        raise ShapeValidationError(
            f"{name} must be two-dimensional (rows, features); got shape {values.shape}."
        )
    if values.size == 0:
        raise ScopeValidationError(f"{name} must contain at least one entry.")
    if not np.all(np.isfinite(values)):
        raise ScopeValidationError(f"{name} must be finite everywhere.")
    return values


def _normalized(values: np.ndarray) -> tuple[np.ndarray, int]:
    """Column-normalize to unit L2 norm, reusing the v0.34c implementation."""
    normalized, _scaling, zero_column_count = column_normalize_design_matrix(values)
    return np.asarray(normalized, dtype=float), int(zero_column_count)


def _validated_support(support: object, n_features: int) -> list[int]:
    if isinstance(support, (str, bytes)) or not isinstance(support, Iterable):
        raise ScopeValidationError(
            "support must be an iterable of integer column indices."
        )
    try:
        indices = [int(i) for i in support]
    except (TypeError, ValueError) as exc:
        raise ScopeValidationError(
            "support must be an iterable of integer column indices."
        ) from exc
    if not indices:
        # Measured: an empty support makes the irrepresentability sum run over an
        # empty axis and return 0.0 -- which reads as "perfectly recoverable"
        # when in fact there is no condition to satisfy. Refuse rather than
        # emit a number that is an artifact of summing nothing.
        raise ScopeValidationError(
            "support must name at least one column; an empty support has no "
            "irrepresentability or restricted-eigenvalue condition to report."
        )
    if len(set(indices)) != len(indices):
        raise ScopeValidationError("support must not repeat a column index.")
    out_of_range = [i for i in indices if not 0 <= i < n_features]
    if out_of_range:
        raise ScopeValidationError(
            f"support indices {out_of_range} are outside the feature range "
            f"[0, {n_features})."
        )
    return sorted(indices)


def mutual_coherence(design_matrix: object) -> dict[str, Any]:
    """Largest absolute correlation between two distinct columns.

    Scale-invariant, so the reported value is unaffected by the normalization;
    it is applied anyway so every metric in this module shares one convention.
    """
    values = _validated_matrix(design_matrix)
    normalized, zero_columns = _normalized(values)

    warnings_out: list[str] = []
    n_features = normalized.shape[1]
    if n_features < 2:
        warnings_out.append("mutual_coherence_requires_at_least_two_columns")
        coherence: float | None = None
    else:
        gram = np.abs(normalized.T @ normalized)
        np.fill_diagonal(gram, 0.0)
        coherence = float(gram.max())
        if coherence >= 1.0 - 1e-12:
            warnings_out.append("mutual_coherence_indicates_collinear_columns")
    if zero_columns:
        warnings_out.append("design_matrix_contains_zero_columns")

    return {
        "metric_name": "mutual_coherence",
        "metric_value": coherence,
        "column_scaling": COLUMN_SCALING_CONVENTION,
        "num_features": int(n_features),
        "zero_column_count": zero_columns,
        "direction": "lower_is_better",
        "interpretation": (
            "Largest absolute inner product between two distinct unit-norm "
            "columns. 0 for an orthonormal design; 1 when two columns are "
            "collinear."
        ),
        "warnings": warnings_out,
        "diagnostic_only": True,
    }


def leverage_scores(design_matrix: object) -> dict[str, Any]:
    """Row leverage from the rank-truncated thin SVD.

    The hat-matrix route ``diag(A (A^T A)^-1 A^T)`` is deliberately not used --
    see the module docstring for the measured error it incurs on ill-conditioned
    input.
    """
    values = _validated_matrix(design_matrix)
    normalized, zero_columns = _normalized(values)

    u, singular_values, _ = np.linalg.svd(normalized, full_matrices=False)
    if singular_values.size:
        tolerance = (
            max(normalized.shape) * float(np.finfo(float).eps) * float(singular_values[0])
        )
    else:  # pragma: no cover - guarded by the empty-matrix check above
        tolerance = 0.0
    rank = int((singular_values > tolerance).sum())
    scores = (u[:, :rank] ** 2).sum(axis=1)

    warnings_out: list[str] = []
    if rank < normalized.shape[1]:
        warnings_out.append("design_matrix_is_column_rank_deficient")
    if zero_columns:
        warnings_out.append("design_matrix_contains_zero_columns")

    return {
        "metric_name": "leverage_scores",
        "leverage_scores": [float(v) for v in scores],
        "max_leverage": float(scores.max()),
        "min_leverage": float(scores.min()),
        "leverage_sum": float(scores.sum()),
        "matrix_rank": rank,
        "num_rows": int(normalized.shape[0]),
        "column_scaling": COLUMN_SCALING_CONVENTION,
        "direction": "lower_max_is_better",
        "interpretation": (
            "Row influence h_i = ||U_i,:||^2 from the thin SVD. Each lies in "
            "[0, 1] and they sum to the matrix rank; a value near 1 marks a row "
            "the fit cannot afford to lose."
        ),
        "warnings": warnings_out,
        "diagnostic_only": True,
    }


def irrepresentability_constant(design_matrix: object, support: object) -> dict[str, Any]:
    """Zhao-Yu irrepresentability constant for a given support.

    Returns ``None`` for ``metric_value`` -- with a warning naming the cause --
    when the quantity is undefined rather than merely large. Measured motivation:
    on a support whose columns are exact duplicates, ``lstsq`` silently returns
    the minimum-norm solution and yields 0.4956551696, which reads as
    "recovery guaranteed" from a singular and therefore meaningless system.
    """
    values = _validated_matrix(design_matrix)
    normalized, zero_columns = _normalized(values)
    indices = _validated_support(support, normalized.shape[1])

    warnings_out: list[str] = []
    if zero_columns:
        warnings_out.append("design_matrix_contains_zero_columns")

    outside = [j for j in range(normalized.shape[1]) if j not in set(indices)]
    if not outside:
        warnings_out.append("irrepresentability_support_covers_all_columns")
        constant: float | None = None
    else:
        support_block = normalized[:, indices]
        support_singular = np.linalg.svd(support_block, compute_uv=False)
        support_tolerance = (
            max(support_block.shape)
            * float(np.finfo(float).eps)
            * float(support_singular[0])
        )
        support_rank = int((support_singular > support_tolerance).sum())
        if support_rank < len(indices):
            # The Gram matrix is singular. A least-squares solve would still
            # return a finite, plausible-looking number from a system that does
            # not determine one.
            warnings_out.append("irrepresentability_support_is_rank_deficient")
            constant = None
        else:
            gram = support_block.T @ support_block
            coefficients = np.linalg.solve(gram, support_block.T @ normalized[:, outside])
            constant = float(np.abs(coefficients).sum(axis=0).max())
            if not math.isfinite(constant):  # pragma: no cover - guarded above
                warnings_out.append("irrepresentability_constant_not_finite")
                constant = None
            elif constant >= 1.0:
                warnings_out.append("irrepresentability_condition_not_satisfied")

    return {
        "metric_name": "irrepresentability_constant",
        "metric_value": constant,
        "support": list(indices),
        "support_size": len(indices),
        "num_features": int(normalized.shape[1]),
        "column_scaling": COLUMN_SCALING_CONVENTION,
        "recovery_threshold": 1.0,
        "condition_satisfied": None if constant is None else bool(constant < 1.0),
        "direction": "lower_is_better",
        "interpretation": (
            "max over columns outside the support of the L1 norm of their "
            "least-squares representation by the support columns. Lasso support "
            "recovery is guaranteed below 1.0. Null when undefined; see warnings."
        ),
        "warnings": warnings_out,
        "diagnostic_only": True,
    }


def restricted_eigenvalue(design_matrix: object, support: object) -> dict[str, Any]:
    """Support-restricted minimum Gram eigenvalue, normalized by the row count.

    This is **not** the full cone-constrained Bickel-Ritov-Tsybakov constant,
    which minimizes over every support of a given size and over a cone and is
    combinatorial to evaluate. This is the exact value for the *given* support,
    and an upper bound on the BRT constant. ``restricted_eigenvalue_definition``
    carries that distinction into the payload.
    """
    values = _validated_matrix(design_matrix)
    normalized, zero_columns = _normalized(values)
    indices = _validated_support(support, normalized.shape[1])

    support_block = normalized[:, indices]
    eigenvalues = np.linalg.eigvalsh(support_block.T @ support_block)
    constant = float(eigenvalues.min() / normalized.shape[0])
    # eigvalsh on a positive-semidefinite Gram can return a tiny negative value
    # from rounding; clamp to zero rather than emit a negative eigenvalue.
    if -1e-12 < constant < 0.0:
        constant = 0.0

    warnings_out: list[str] = []
    if zero_columns:
        warnings_out.append("design_matrix_contains_zero_columns")

    support_singular = np.linalg.svd(support_block, compute_uv=False)
    support_tolerance = (
        max(support_block.shape) * float(np.finfo(float).eps) * float(support_singular[0])
    )
    support_rank = int((support_singular > support_tolerance).sum())
    if support_rank < len(indices):
        # Measured: a rank-deficient support and a merely ill-conditioned one
        # both produce a near-zero value (0.0 vs 2.162100e-12 on the probes).
        # Only the rank check separates "degenerate" from "small".
        warnings_out.append("restricted_eigenvalue_support_is_rank_deficient")
    if not math.isfinite(constant):  # pragma: no cover - Gram of finite input
        warnings_out.append("restricted_eigenvalue_not_finite")

    return {
        "metric_name": "restricted_eigenvalue",
        "metric_value": constant if math.isfinite(constant) else None,
        "restricted_eigenvalue_definition": RESTRICTED_EIGENVALUE_DEFINITION,
        "support": list(indices),
        "support_size": len(indices),
        "support_rank": support_rank,
        "num_rows": int(normalized.shape[0]),
        "column_scaling": COLUMN_SCALING_CONVENTION,
        "sqrt_n_convention_multiplier": int(normalized.shape[0]),
        "direction": "higher_is_better",
        "interpretation": (
            "Smallest eigenvalue of the support Gram matrix divided by the row "
            "count, under unit-norm columns. Larger means the support columns "
            "are better separated. Multiply by sqrt_n_convention_multiplier for "
            "the ||a_j|| = sqrt(n) convention."
        ),
        "warnings": warnings_out,
        "diagnostic_only": True,
    }


def summarize_design_matrix_diagnostics(
    design_matrix: object, *, support: object
) -> dict[str, Any]:
    """All four diagnostics under one column-scaling convention.

    ``support`` is required rather than defaulting: two of the four metrics are
    undefined without one, and a default would invite reading a value computed
    against an arbitrary support as though it described the matrix alone.
    """
    values = _validated_matrix(design_matrix)
    coherence = mutual_coherence(values)
    leverage = leverage_scores(values)
    irrepresentability = irrepresentability_constant(values, support)
    restricted = restricted_eigenvalue(values, support)

    aggregated: list[str] = []
    for block in (coherence, leverage, irrepresentability, restricted):
        for warning in block["warnings"]:
            if warning not in aggregated:
                aggregated.append(warning)

    return {
        "summary_type": "pdelie_design_matrix_diagnostic",
        "num_rows": int(values.shape[0]),
        "num_features": int(values.shape[1]),
        "column_scaling": COLUMN_SCALING_CONVENTION,
        "support": list(irrepresentability["support"]),
        "mutual_coherence": coherence,
        "leverage_scores": leverage,
        "irrepresentability_constant": irrepresentability,
        "restricted_eigenvalue": restricted,
        "warnings": aggregated,
        "diagnostic_only": True,
    }
