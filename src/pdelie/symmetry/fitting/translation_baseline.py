from __future__ import annotations

import numpy as np

from pdelie.contracts import FieldBatch, GeneratorFamily
from pdelie.residuals.base import ResidualEvaluator
from pdelie.symmetry.parameterization.polynomial_translation import (
    POLYNOMIAL_TRANSLATION_BASIS,
    apply_pointwise_translation,
    build_translation_basis,
    normalize_translation_coefficients,
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
    for basis_name in POLYNOMIAL_TRANSLATION_BASIS:
        transformed = apply_pointwise_translation(field, basis[basis_name], epsilon)
        transformed_residual = residual_evaluator.evaluate(transformed).residual
        delta = (transformed_residual - baseline_residual) / epsilon
        columns.append(delta.reshape(-1))

    design = np.column_stack(columns)
    _, singular_values, vh = np.linalg.svd(design, full_matrices=False)
    coefficients = normalize_translation_coefficients(vh[-1])

    return GeneratorFamily(
        parameterization="polynomial_translation_affine",
        coefficients=coefficients,
        normalization="l2_unit",
        diagnostics={
            "basis": list(POLYNOMIAL_TRANSLATION_BASIS),
            "fit_residual": float(singular_values[-1]),
            "training_epsilon": float(epsilon),
        },
    )

