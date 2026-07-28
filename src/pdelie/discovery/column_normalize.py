"""v0.34c: column normalization for weak-form design matrices.

Pure NumPy. No PySINDy import, no backend dependency.

**This is a conditioning fix, not a noise-robustness fix.** Column normalization
rescales each design-matrix column to unit L2 norm so that the least-squares
problem is posed on comparably-scaled columns. It changes the *numerical
conditioning* of the fit. It makes no claim about robustness to measurement
noise, and it is not WSINDy.

The measured effect is real but modest and highly fixture-dependent. Across the
six fixtures pinned in ``tests/fixtures/v0_34c_conditioning_ratios.json`` (at the
fixed seed those values require) the condition-number improvement ranges from
**1.79x to 48.34x**, median **4.51x**. The canonical fixture -- the one a reader
is most likely to assume a headline figure describes -- improves by under 2x.
Read the per-fixture numbers; there is no single representative figure.

Reproducibility caveat
----------------------

``pysindy.WeakPDELibrary`` places its ``K`` domain centers by drawing from the
global NumPy RNG and exposes no seed parameter, so these quantities are
nondeterministic unless
``inspect_pysindy_weak_pde_library(..., seed=...)`` is used. Unseeded, the
canonical fixture's ``condition_number_before_normalization`` was measured
anywhere in 5.03-14.44 across 12 draws.

Threshold semantics under normalization
---------------------------------------

STLSQ thresholds the *coefficients*, so running it on a normalized matrix
thresholds normalized coefficients. Those correspond to different physical
magnitudes than the raw ones. :func:`rescale_coefficients` inverts the scaling
after the fit, but the thresholding decision was still made in normalized space
-- callers comparing sparsity patterns across the two paths must account for it.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from pdelie.errors import ScopeValidationError, ShapeValidationError

__all__ = [
    "column_normalize_design_matrix",
    "rescale_coefficients",
    "summarize_column_normalization",
]


def _validate_design_matrix(design_matrix: object) -> np.ndarray:
    matrix = np.asarray(design_matrix, dtype=float)
    if matrix.ndim != 2:
        raise ShapeValidationError(
            f"design_matrix must be two-dimensional (rows, columns); got shape {matrix.shape}."
        )
    if matrix.size == 0:
        raise ShapeValidationError("design_matrix must not be empty.")
    if not np.all(np.isfinite(matrix)):
        raise ScopeValidationError("design_matrix must be finite everywhere.")
    return matrix


def column_normalize_design_matrix(
    design_matrix: object,
) -> tuple[np.ndarray, np.ndarray, int]:
    """Scale each column to unit L2 norm.

    Returns ``(normalized_matrix, scaling_vector, zero_column_count)``.

    A column whose L2 norm is exactly zero carries no information and cannot be
    normalized. Its scale is set to ``1.0`` rather than dividing by zero, which
    leaves the column untouched, and the count is reported so the caller can see
    it happened instead of inferring it from a silently-unchanged column.
    """
    matrix = _validate_design_matrix(design_matrix)
    norms = np.linalg.norm(matrix, axis=0)
    zero_column_count = int(np.count_nonzero(norms == 0.0))
    scaling_vector = np.where(norms == 0.0, 1.0, norms)
    return matrix / scaling_vector, scaling_vector, zero_column_count


def rescale_coefficients(
    coefficients: object, scaling_vector: object
) -> np.ndarray:
    """Invert the column scaling on coefficients fitted in normalized space.

    Fitting ``y ~ (M / s) b_norm`` and fitting ``y ~ M b_raw`` are related by
    ``b_raw = b_norm / s``, so the recovered coefficients are divided by the
    same scaling vector applied to the columns.

    ``coefficients`` may be 1-D ``(n_features,)`` or 2-D ``(n_targets,
    n_features)``; the scaling is applied along the feature axis.
    """
    values = np.asarray(coefficients, dtype=float)
    scale = np.asarray(scaling_vector, dtype=float)
    if scale.ndim != 1:
        raise ShapeValidationError("scaling_vector must be one-dimensional.")
    if values.shape[-1] != scale.size:
        raise ShapeValidationError(
            f"coefficients last axis ({values.shape[-1]}) must match the scaling "
            f"vector length ({scale.size})."
        )
    if not np.all(np.isfinite(values)):
        raise ScopeValidationError("coefficients must be finite everywhere.")
    return np.asarray(values / scale, dtype=float)


def summarize_column_normalization(design_matrix: object) -> dict[str, Any]:
    """Strict-JSON diagnostic block describing the normalization of one matrix.

    ``diagnostic_only`` is always ``True``: this block reports conditioning, it
    does not license any claim about recovery quality or noise robustness.
    """
    matrix = _validate_design_matrix(design_matrix)
    normalized, scaling_vector, zero_column_count = column_normalize_design_matrix(matrix)

    condition_before = float(np.linalg.cond(matrix))
    condition_after = float(np.linalg.cond(normalized))
    smallest = float(scaling_vector.min())
    largest = float(scaling_vector.max())

    return {
        "applied": True,
        "column_scale_ratio": (largest / smallest) if smallest > 0.0 else None,
        "condition_number_before_normalization": (
            condition_before if np.isfinite(condition_before) else None
        ),
        "condition_number_after_normalization": (
            condition_after if np.isfinite(condition_after) else None
        ),
        "condition_number_improvement_ratio": (
            float(condition_before / condition_after)
            if np.isfinite(condition_before) and np.isfinite(condition_after) and condition_after > 0.0
            else None
        ),
        "scaling_vector_l2_norm": float(np.linalg.norm(scaling_vector)),
        "scaling_zero_column_count": zero_column_count,
        "diagnostic_only": True,
    }
