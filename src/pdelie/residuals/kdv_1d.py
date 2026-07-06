from __future__ import annotations

from collections.abc import Mapping

import numpy as np

from pdelie._boundary import is_x_periodic
from pdelie.contracts import DerivativeBatch, FieldBatch, ResidualBatch
from pdelie.derivatives import compute_spectral_fd_derivatives
from pdelie.errors import SchemaValidationError, ScopeValidationError
from pdelie.residuals.base import ResidualEvaluator


_KDV_EQUATION = "u_t + 6*u*u_x + u_xxx = 0"
_REQUIRED_DERIVATIVES = ("u_t", "u_x", "u_xxx")


def _validate_kdv_field(field: FieldBatch) -> None:
    field.validate()

    if field.dims != ("batch", "time", "x", "var"):
        raise ScopeValidationError("KdVResidualEvaluator only supports dims ('batch', 'time', 'x', 'var').")
    if len(field.var_names) != 1 or field.values.shape[-1] != 1:
        raise ScopeValidationError("KdVResidualEvaluator only supports scalar FieldBatch inputs.")
    if field.mask is not None:
        raise ScopeValidationError("KdVResidualEvaluator does not support masked fields.")
    if not np.all(np.isfinite(field.values)):
        raise ScopeValidationError("KdVResidualEvaluator requires finite field values.")

    if not is_x_periodic(field):
        raise ScopeValidationError("KdVResidualEvaluator requires periodic boundary conditions in x.")

    parameter_tags = field.metadata.get("parameter_tags")
    if not isinstance(parameter_tags, Mapping):
        raise SchemaValidationError("KdVResidualEvaluator requires field.metadata['parameter_tags'] to be a mapping.")
    if parameter_tags.get("equation") != "kdv_normalized":
        raise ScopeValidationError(
            "KdVResidualEvaluator requires field.metadata['parameter_tags']['equation'] == 'kdv_normalized'."
        )


class KdVResidualEvaluator(ResidualEvaluator):
    def evaluate(
        self,
        field: FieldBatch,
        derivatives: DerivativeBatch | None = None,
    ) -> ResidualBatch:
        _validate_kdv_field(field)
        if derivatives is None:
            derivatives = compute_spectral_fd_derivatives(field, max_spatial_order=3)
        derivatives.validate_against(field)

        for name in _REQUIRED_DERIVATIVES:
            if name not in derivatives.derivatives:
                raise SchemaValidationError(f"KdVResidualEvaluator requires derivative '{name}'.")

        u = np.asarray(field.values, dtype=float)
        residual = (
            derivatives.derivatives["u_t"]
            + 6.0 * u * derivatives.derivatives["u_x"]
            + derivatives.derivatives["u_xxx"]
        )
        batch = ResidualBatch(
            residual=residual,
            definition_type="analytic",
            normalization="none",
            diagnostics={
                "backend": derivatives.backend,
                "equation": _KDV_EQUATION,
                "max_abs_residual": float(np.max(np.abs(residual))),
                "rms_residual": float(np.sqrt(np.mean(np.square(residual)))),
            },
        )
        batch.validate_against(field)
        return batch
