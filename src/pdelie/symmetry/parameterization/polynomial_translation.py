from __future__ import annotations

import numpy as np

from pdelie._boundary import is_x_periodic
from pdelie.contracts import FieldBatch
from pdelie.errors import ScopeValidationError, ShapeValidationError

POLYNOMIAL_TRANSLATION_BASIS = ("1", "t", "x", "u")
DEFAULT_TRANSLATION_SPAN_TOLERANCE = 5e-2


def _coerce_translation_coefficients(coefficients: np.ndarray) -> np.ndarray:
    coefficients = np.asarray(coefficients, dtype=float)
    if coefficients.ndim == 1 and coefficients.size == len(POLYNOMIAL_TRANSLATION_BASIS):
        return coefficients
    if coefficients.ndim == 2 and coefficients.shape == (1, len(POLYNOMIAL_TRANSLATION_BASIS)):
        return coefficients[0]
    if coefficients.ndim == 2 and coefficients.shape[0] != 1:
        raise ShapeValidationError("Stable translation helpers only support a single translation generator row.")
    raise ShapeValidationError(
        "Translation coefficients must be a one-dimensional array of length "
        f"{len(POLYNOMIAL_TRANSLATION_BASIS)} or a two-dimensional single-row array "
        f"of shape (1, {len(POLYNOMIAL_TRANSLATION_BASIS)})."
    )


def build_translation_basis(field: FieldBatch) -> dict[str, np.ndarray]:
    field.validate()
    if field.dims != ("batch", "time", "x", "var"):
        raise ScopeValidationError("The stable translation basis only supports dims ('batch', 'time', 'x', 'var').")
    if len(field.var_names) != 1:
        raise ScopeValidationError("The stable translation basis only supports a single scalar variable.")

    # v0.33a: no boundary-condition gate. The basis {1, t, x, u} is built from
    # coordinates and values alone and is boundary-condition-agnostic; the
    # periodic requirement lived here only because every consumer was periodic.
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
    coefficients = _coerce_translation_coefficients(coefficients)
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
    for weight, name in zip(coefficients, POLYNOMIAL_TRANSLATION_BASIS, strict=False):
        xi += weight * basis[name]
    return xi


def apply_pointwise_translation(field: FieldBatch, xi: np.ndarray, epsilon: float) -> FieldBatch:
    """Translate a field pointwise by ``epsilon * xi``.

    Dispatches on the x boundary condition (v0.33a):

    * **Periodic** — unchanged. The query wraps modulo the period, so every
      output row is interpolated from genuine in-domain data.
    * **Nonperiodic** — no wrap. ``np.interp`` clamps to the edge values outside
      ``[x[0], x[-1]]``, so rows within roughly ``epsilon * max|xi| / dx`` of a
      boundary are extrapolated rather than translated. Those rows are **not**
      trustworthy; ``fit_translation_generator`` discards them via the
      interior-only shave before the SVD sees them. Callers using this helper
      directly on nonperiodic data must apply their own shave.
    """
    xi = np.asarray(xi, dtype=float)
    if xi.shape != field.values.shape:
        raise ScopeValidationError("Pointwise translation xi must match the FieldBatch shape.")

    x = field.coords["x"]
    transformed = np.empty_like(field.values)

    if is_x_periodic(field):
        dx = float(x[1] - x[0])
        period = float(x[-1] - x[0] + dx)
        x0 = float(x[0])
        xp_ext = np.concatenate((x - period, x, x + period))
        for batch_index in range(field.values.shape[0]):
            for time_index in range(field.values.shape[1]):
                for var_index in range(field.values.shape[3]):
                    row = field.values[batch_index, time_index, :, var_index]
                    shift = epsilon * xi[batch_index, time_index, :, var_index]
                    query = ((x - shift - x0) % period) + x0
                    fp_ext = np.concatenate((row, row, row))
                    transformed[batch_index, time_index, :, var_index] = np.interp(
                        query, xp_ext, fp_ext
                    )
    else:
        # v0.33a: no wrap. np.interp clamps to the edge values off-domain, so
        # near-boundary rows are extrapolated rather than translated; callers
        # must shave them (fit_translation_generator does).
        for batch_index in range(field.values.shape[0]):
            for time_index in range(field.values.shape[1]):
                for var_index in range(field.values.shape[3]):
                    row = field.values[batch_index, time_index, :, var_index]
                    shift = epsilon * xi[batch_index, time_index, :, var_index]
                    transformed[batch_index, time_index, :, var_index] = np.interp(
                        x - shift, x, row
                    )

    return FieldBatch(
        values=transformed,
        dims=field.dims,
        coords={name: coord.copy() for name, coord in field.coords.items()},
        var_names=list(field.var_names),
        metadata=dict(field.metadata),
        preprocess_log=list(field.preprocess_log),
        mask=None if field.mask is None else field.mask.copy(),
    )
