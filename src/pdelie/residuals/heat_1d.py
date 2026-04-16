from __future__ import annotations

import numpy as np

from pdelie.contracts import DerivativeBatch, FieldBatch, ResidualBatch
from pdelie.derivatives import compute_spectral_fd_derivatives
from pdelie.errors import SchemaValidationError
from pdelie.residuals.base import ResidualEvaluator


class HeatResidualEvaluator(ResidualEvaluator):
    def __init__(self, diffusivity: float | None = None) -> None:
        self.diffusivity = diffusivity

    def evaluate(
        self,
        field: FieldBatch,
        derivatives: DerivativeBatch | None = None,
    ) -> ResidualBatch:
        field.validate()
        if derivatives is None:
            derivatives = compute_spectral_fd_derivatives(field)
        derivatives.validate_against(field)

        for name in ("u_t", "u_xx"):
            if name not in derivatives.derivatives:
                raise SchemaValidationError(f"HeatResidualEvaluator requires derivative '{name}'.")

        diffusivity = self.diffusivity
        if diffusivity is None:
            diffusivity = float(field.metadata["parameter_tags"]["nu"])

        residual = derivatives.derivatives["u_t"] - diffusivity * derivatives.derivatives["u_xx"]
        batch = ResidualBatch(
            residual=residual,
            definition_type="analytic",
            normalization="none",
            diagnostics={
                "backend": derivatives.backend,
                "nu": diffusivity,
                "max_abs_residual": float(np.max(np.abs(residual))),
            },
        )
        batch.validate_against(field)
        return batch

