from __future__ import annotations

import numpy as np

from pdelie.contracts import FieldBatch
from pdelie.errors import ScopeValidationError, ShapeValidationError


POLYNOMIAL_TRANSLATION_BASIS = ("1", "t", "x", "u")


def build_translation_basis(field: FieldBatch) -> dict[str, np.ndarray]:
    field.validate()
    if field.dims != ("batch", "time", "x", "var"):
        raise ScopeValidationError("The V0.1 translation basis only supports 1D heat FieldBatch inputs.")

    ones = np.ones_like(field.values)
    time_values = field.coords["time"][None, :, None, None]
    x_values = field.coords["x"][None, None, :, None]
    return {
        "1": ones,
        "t": np.broadcast_to(time_values, field.values.shape),
        "x": np.broadcast_to(x_values, field.values.shape),
        "u": np.asarray(field.values, dtype=float),
    }


def normalize_translation_coefficients(coefficients: np.ndarray) -> np.ndarray:
    coefficients = np.asarray(coefficients, dtype=float)
    norm = np.linalg.norm(coefficients)
    if norm == 0.0:
        raise ShapeValidationError("Translation coefficients must not be the zero vector.")
    normalized = coefficients / norm
    if normalized[0] < 0.0:
        normalized = -normalized
    return normalized


def translation_reference_coefficients() -> np.ndarray:
    return np.array([1.0, 0.0, 0.0, 0.0], dtype=float)


def translation_span_distance(coefficients: np.ndarray) -> float:
    normalized = normalize_translation_coefficients(coefficients)
    reference = translation_reference_coefficients()
    return float(min(np.linalg.norm(normalized - reference), np.linalg.norm(normalized + reference)))


def evaluate_translation_xi(field: FieldBatch, coefficients: np.ndarray) -> np.ndarray:
    coefficients = normalize_translation_coefficients(coefficients)
    basis = build_translation_basis(field)
    xi = np.zeros_like(field.values, dtype=float)
    for weight, name in zip(coefficients, POLYNOMIAL_TRANSLATION_BASIS):
        xi += weight * basis[name]
    return xi


def apply_pointwise_translation(field: FieldBatch, xi: np.ndarray, epsilon: float) -> FieldBatch:
    xi = np.asarray(xi, dtype=float)
    if xi.shape != field.values.shape:
        raise ScopeValidationError("Pointwise translation xi must match the FieldBatch shape.")

    x = field.coords["x"]
    dx = float(x[1] - x[0])
    period = float(x[-1] - x[0] + dx)
    x0 = float(x[0])

    transformed = np.empty_like(field.values)
    xp = x

    for batch_index in range(field.values.shape[0]):
        for time_index in range(field.values.shape[1]):
            for var_index in range(field.values.shape[3]):
                row = field.values[batch_index, time_index, :, var_index]
                shift = epsilon * xi[batch_index, time_index, :, var_index]
                query = ((x - shift - x0) % period) + x0
                xp_ext = np.concatenate((xp - period, xp, xp + period))
                fp_ext = np.concatenate((row, row, row))
                transformed[batch_index, time_index, :, var_index] = np.interp(query, xp_ext, fp_ext)

    return FieldBatch(
        values=transformed,
        dims=field.dims,
        coords={name: coord.copy() for name, coord in field.coords.items()},
        var_names=list(field.var_names),
        metadata=dict(field.metadata),
        preprocess_log=list(field.preprocess_log),
        mask=None if field.mask is None else field.mask.copy(),
    )
