from __future__ import annotations

import numpy as np

from pdelie.contracts import FieldBatch, GeneratorFamily, VerificationReport
from pdelie.errors import ScopeValidationError
from pdelie.residuals.base import ResidualEvaluator
from pdelie.symmetry.parameterization.polynomial_translation import (
    apply_pointwise_translation,
    evaluate_translation_xi,
    translation_span_distance,
)


DEFAULT_EPSILON_VALUES = np.logspace(-4, -1, 7)
DEFAULT_RELATIVE_L2_NORM = "relative_l2"


def _apply_uniform_translation(field: FieldBatch, shift: float) -> FieldBatch:
    if field.metadata["boundary_conditions"].get("x") != "periodic":
        raise ScopeValidationError("Uniform translation requires periodic boundary conditions in x.")
    x = field.coords["x"]
    dx = float(x[1] - x[0])
    x_axis = field.dims.index("x")
    wavenumbers = 2.0 * np.pi * np.fft.fftfreq(x.size, d=dx)
    phase = np.exp(-1j * wavenumbers * shift)
    reshape = [1] * field.values.ndim
    reshape[x_axis] = x.size
    shifted_values = np.real(
        np.fft.ifft(np.fft.fft(field.values, axis=x_axis) * phase.reshape(tuple(reshape)), axis=x_axis)
    )
    return FieldBatch(
        values=shifted_values,
        dims=field.dims,
        coords={name: coord.copy() for name, coord in field.coords.items()},
        var_names=list(field.var_names),
        metadata=dict(field.metadata),
        preprocess_log=list(field.preprocess_log),
        mask=None if field.mask is None else field.mask.copy(),
    )


def _relative_l2(error: np.ndarray, reference: np.ndarray) -> float:
    return float(np.linalg.norm(error) / (np.linalg.norm(reference) + 1e-12))


def _classify_error_curve(error_curve: np.ndarray) -> str:
    e_small = float(error_curve[0])
    e_max = float(np.max(error_curve))

    monotone_curve = bool(np.all(np.diff(error_curve) >= -1e-12))
    stable_curve = monotone_curve and e_max <= 1e-4
    bounded_curve = e_max <= 1e-1

    if e_small <= 1e-6 and stable_curve:
        return "exact"
    if e_small <= 1e-2 and bounded_curve:
        return "approximate"
    return "failed"


def verify_translation_generator(
    field: FieldBatch,
    generator: GeneratorFamily,
    residual_evaluator: ResidualEvaluator,
    *,
    epsilon_values: np.ndarray | None = None,
    min_heldout_initial_conditions: int = 3,
    span_tolerance: float = 5e-2,
) -> VerificationReport:
    field.validate()
    generator.validate()

    if field.values.shape[0] < min_heldout_initial_conditions:
        raise ScopeValidationError(
            f"Held-out verification requires at least {min_heldout_initial_conditions} unseen initial conditions in V0.1."
        )

    epsilon_values = DEFAULT_EPSILON_VALUES if epsilon_values is None else np.asarray(epsilon_values, dtype=float)
    span_distance = translation_span_distance(generator.coefficients)
    baseline_residual = residual_evaluator.evaluate(field).residual

    xi = evaluate_translation_xi(field, generator.coefficients)
    use_uniform_translation = span_distance <= span_tolerance
    batch_errors: list[list[float]] = []

    for epsilon in epsilon_values:
        if use_uniform_translation:
            transformed = _apply_uniform_translation(field, float(epsilon * generator.coefficients[0]))
        else:
            transformed = apply_pointwise_translation(field, xi, float(epsilon))

        transformed_residual = residual_evaluator.evaluate(transformed).residual
        diff = transformed_residual - baseline_residual
        epsilon_batch_errors = [
            _relative_l2(diff[batch_index], field.values[batch_index])
            for batch_index in range(field.values.shape[0])
        ]
        batch_errors.append(epsilon_batch_errors)

    error_curve = np.median(np.asarray(batch_errors, dtype=float), axis=1)
    classification = _classify_error_curve(error_curve)
    if not use_uniform_translation:
        classification = "failed"

    return VerificationReport(
        norm=DEFAULT_RELATIVE_L2_NORM,
        epsilon_values=epsilon_values,
        error_curve=error_curve,
        classification=classification,
        diagnostics={
            "heldout_initial_conditions": int(field.values.shape[0]),
            "span_distance": float(span_distance),
            "span_tolerance": float(span_tolerance),
            "transform_mode": "uniform_translation" if use_uniform_translation else "pointwise_translation",
            "batch_errors": batch_errors,
        },
    )
