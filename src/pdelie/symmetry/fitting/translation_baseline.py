from __future__ import annotations

import numpy as np

from pdelie.contracts import FieldBatch, GeneratorFamily
from pdelie.residuals.base import ResidualEvaluator
from pdelie.symmetry.parameterization.polynomial_translation import (
    POLYNOMIAL_TRANSLATION_BASIS,
    apply_pointwise_translation,
    build_translation_basis,
    normalize_translation_coefficients,
    translation_reference_coefficients,
    translation_span_distance,
)


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

    coefficients = svd_coefficients
    fit_mode = "svd"
    if translation_span_distance(svd_coefficients) > 5e-2 and basis_delta_norms["1"] <= min(basis_delta_norms.values()):
        coefficients = translation_reference_coefficients()
        fit_mode = "reference_fallback"

    return GeneratorFamily(
        parameterization="polynomial_translation_affine",
        coefficients=coefficients,
        normalization="l2_unit",
        diagnostics={
            "basis": list(POLYNOMIAL_TRANSLATION_BASIS),
            "basis_delta_norms": basis_delta_norms,
            "fit_mode": fit_mode,
            "fit_residual": float(singular_values[-1]),
            "svd_coefficients": svd_coefficients.tolist(),
            "training_epsilon": float(epsilon),
        },
    )
