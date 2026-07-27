from __future__ import annotations

import warnings

import numpy as np

from pdelie._boundary import get_x_boundary_type, is_x_periodic
from pdelie.contracts import FieldBatch, GeneratorFamily, _translation_generator_basis_spec
from pdelie.residuals.base import ResidualEvaluator
from pdelie.symmetry.parameterization.polynomial_translation import (
    DEFAULT_TRANSLATION_SPAN_TOLERANCE,
    POLYNOMIAL_TRANSLATION_BASIS,
    apply_pointwise_translation,
    build_translation_basis,
    normalize_translation_coefficients,
    translation_reference_coefficients,
    translation_span_distance,
)

TRANSLATION_FALLBACK_SPAN_TOLERANCE = DEFAULT_TRANSLATION_SPAN_TOLERANCE

#: Below this many retained interior rows the interior-only SVD is poorly
#: conditioned and the fit should not be trusted; a warning is emitted.
MINIMUM_INTERIOR_ROW_COUNT = 12

#: v0.33a claim-label vocabulary (frozen by the v0.33 scope amendment).
SYMMETRY_CLAIM_EQUATION_CANDIDATE = "equation_symmetry_candidate"
SYMMETRY_CLAIM_INCONCLUSIVE_BOUNDARY = "inconclusive_boundary_metadata"


def _condition_number(singular_values: np.ndarray) -> float | None:
    largest = float(singular_values[0])
    smallest = float(singular_values[-1])
    if not np.isfinite(largest) or not np.isfinite(smallest) or smallest == 0.0:
        return None
    return largest / smallest


def _translation_evidence_label(
    *,
    reference_fallback_used: bool,
    svd_span_distance: float,
) -> str:
    if reference_fallback_used:
        return "reference_fallback"
    if svd_span_distance <= TRANSLATION_FALLBACK_SPAN_TOLERANCE:
        return "direct_svd_in_tolerance"
    return "direct_svd_out_of_tolerance"


def _select_translation_coefficients(
    svd_coefficients: np.ndarray,
    basis_delta_norms: dict[str, float],
    *,
    allow_reference_fallback: bool = True,
) -> tuple[np.ndarray, str, bool, str | None, str]:
    """Choose the emitted coefficients, optionally without the reference fallback.

    The reference fallback exists to hand callers a usable pure-translation
    generator when the SVD direction drifts. It has a hard cost: the emitted
    ``span_distance`` becomes exactly ``0.0`` regardless of how badly the fit
    actually drifted, because the reference coefficients are at distance zero
    from themselves.

    On the nonperiodic branch that cost is unacceptable and the fallback is
    suppressed (v0.33a). Measurement across all four supported PDEs found the
    fallback firing on three of them, reporting ``span_distance = 0.0`` where
    the honest SVD values were 0.24-0.64 -- i.e. reporting a *perfect*
    translation generator on fits that had substantially drifted. The periodic
    branch keeps the fallback unchanged, preserving byte-for-byte behaviour.
    """
    svd_span_distance = translation_span_distance(svd_coefficients)
    min_delta_basis = min(basis_delta_norms, key=basis_delta_norms.get)

    if not allow_reference_fallback:
        return (
            svd_coefficients,
            "svd",
            False,
            "reference_fallback_suppressed_on_nonperiodic_branch",
            min_delta_basis,
        )

    if svd_span_distance > TRANSLATION_FALLBACK_SPAN_TOLERANCE and min_delta_basis == "1":
        return (
            translation_reference_coefficients(),
            "reference_fallback",
            True,
            "svd_translation_span_drift",
            min_delta_basis,
        )

    return svd_coefficients, "svd", False, None, min_delta_basis


def fit_translation_generator(
    field: FieldBatch,
    residual_evaluator: ResidualEvaluator,
    *,
    epsilon: float = 1e-4,
) -> GeneratorFamily:
    field.validate()
    basis = build_translation_basis(field)
    baseline = residual_evaluator.evaluate(field)
    baseline_residual = baseline.residual

    periodic = is_x_periodic(field)
    x_axis = field.dims.index("x")
    full_row_count = int(field.values.shape[x_axis])

    # v0.33a interior-only shave. The shave width is read from the residual
    # diagnostics rather than hardcoded, so it tracks whatever the finite
    # difference backend actually trims. Measurement showed a fixed 1-row shave
    # leaves contaminated boundary rows dominating the SVD: span_distance sat
    # near the sqrt(2) ceiling on all four PDEs until the shave matched
    # boundary_trim_width, at which point Heat collapsed from 1.13 to 0.0043.
    if periodic:
        trim = 0
    else:
        trim = int(baseline.diagnostics.get("boundary_trim_width", 0))
    interior_only_reduction_applied = bool(trim > 0)
    interior_only_row_count = full_row_count - 2 * trim if trim > 0 else full_row_count

    if interior_only_reduction_applied and interior_only_row_count < MINIMUM_INTERIOR_ROW_COUNT:
        warnings.warn(
            f"Nonperiodic translation fit retained only {interior_only_row_count} interior "
            f"rows after trimming {trim} on each side of {full_row_count}; the interior-only "
            "SVD is poorly conditioned below "
            f"{MINIMUM_INTERIOR_ROW_COUNT} rows and the resulting generator should not be "
            "trusted. Increase num_points.",
            UserWarning,
            stacklevel=2,
        )

    def _shave(delta: np.ndarray) -> np.ndarray:
        if trim <= 0:
            return delta
        slicer: list[slice] = [slice(None)] * delta.ndim
        slicer[x_axis] = slice(trim, delta.shape[x_axis] - trim)
        return delta[tuple(slicer)]

    columns: list[np.ndarray] = []
    basis_delta_norms: dict[str, float] = {}
    for basis_name in POLYNOMIAL_TRANSLATION_BASIS:
        transformed = apply_pointwise_translation(field, basis[basis_name], epsilon)
        transformed_residual = residual_evaluator.evaluate(transformed).residual
        delta = _shave((transformed_residual - baseline_residual) / epsilon)
        flattened = delta.reshape(-1)
        columns.append(flattened)
        basis_delta_norms[basis_name] = float(np.linalg.norm(flattened))

    design = np.column_stack(columns)
    _, singular_values, vh = np.linalg.svd(design, full_matrices=False)
    svd_coefficients = normalize_translation_coefficients(vh[-1])
    svd_span_distance = float(translation_span_distance(svd_coefficients))

    coefficients, fit_mode, reference_fallback_used, fallback_reason, min_delta_basis = _select_translation_coefficients(
        svd_coefficients,
        basis_delta_norms,
        allow_reference_fallback=periodic,
    )
    selected_span_distance = float(translation_span_distance(coefficients))

    boundary_condition_x = get_x_boundary_type(field)
    symmetry_claim = (
        SYMMETRY_CLAIM_INCONCLUSIVE_BOUNDARY
        if boundary_condition_x == "open_unknown"
        else SYMMETRY_CLAIM_EQUATION_CANDIDATE
    )

    return GeneratorFamily(
        parameterization="polynomial_translation_affine",
        coefficients=coefficients.reshape(1, -1),
        basis_spec=_translation_generator_basis_spec(),
        normalization="l2_unit",
        diagnostics={
            "basis": list(POLYNOMIAL_TRANSLATION_BASIS),
            "basis_delta_norms": basis_delta_norms,
            "boundary_condition_dispatch_reason": (
                "is_x_periodic_true" if periodic else "is_x_periodic_false_field_metadata"
            ),
            "boundary_condition_x": boundary_condition_x,
            "condition_number": _condition_number(singular_values),
            "design_column_norms": dict(basis_delta_norms),
            "evidence_label": _translation_evidence_label(
                reference_fallback_used=reference_fallback_used,
                svd_span_distance=svd_span_distance,
            ),
            "fallback_reason": fallback_reason,
            "fit_mode": fit_mode,
            "fit_residual": float(singular_values[-1]),
            "interior_only_reduction_applied": interior_only_reduction_applied,
            "interior_only_row_count": int(interior_only_row_count),
            "interior_only_trim_width": int(trim),
            "min_delta_basis": min_delta_basis,
            "reference_fallback_used": reference_fallback_used,
            "selected_coefficients": coefficients.tolist(),
            "selected_span_distance": selected_span_distance,
            "singular_values": singular_values.tolist(),
            "svd_coefficients": svd_coefficients.tolist(),
            "svd_span_distance": svd_span_distance,
            "symmetry_claim": symmetry_claim,
            "training_epsilon": float(epsilon),
        },
    )
