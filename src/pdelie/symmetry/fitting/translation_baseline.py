from __future__ import annotations

import numpy as np

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
) -> tuple[np.ndarray, str, bool, str | None, str]:
    svd_span_distance = translation_span_distance(svd_coefficients)
    min_delta_basis = min(basis_delta_norms, key=basis_delta_norms.get)

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
    baseline_residual = residual_evaluator.evaluate(field).residual

    columns: list[np.ndarray] = []
    basis_delta_norms: dict[str, float] = {}
    for basis_name in POLYNOMIAL_TRANSLATION_BASIS:
        transformed = apply_pointwise_translation(field, basis[basis_name], epsilon)
        transformed_residual = residual_evaluator.evaluate(transformed).residual
        delta = (transformed_residual - baseline_residual) / epsilon
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
    )
    selected_span_distance = float(translation_span_distance(coefficients))

    return GeneratorFamily(
        parameterization="polynomial_translation_affine",
        coefficients=coefficients.reshape(1, -1),
        basis_spec=_translation_generator_basis_spec(),
        normalization="l2_unit",
        diagnostics={
            "basis": list(POLYNOMIAL_TRANSLATION_BASIS),
            "basis_delta_norms": basis_delta_norms,
            "condition_number": _condition_number(singular_values),
            "design_column_norms": dict(basis_delta_norms),
            "evidence_label": _translation_evidence_label(
                reference_fallback_used=reference_fallback_used,
                svd_span_distance=svd_span_distance,
            ),
            "fallback_reason": fallback_reason,
            "fit_mode": fit_mode,
            "fit_residual": float(singular_values[-1]),
            "min_delta_basis": min_delta_basis,
            "reference_fallback_used": reference_fallback_used,
            "selected_coefficients": coefficients.tolist(),
            "selected_span_distance": selected_span_distance,
            "singular_values": singular_values.tolist(),
            "svd_coefficients": svd_coefficients.tolist(),
            "svd_span_distance": svd_span_distance,
            "training_epsilon": float(epsilon),
        },
    )
