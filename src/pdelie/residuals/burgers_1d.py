from __future__ import annotations

import numpy as np

from pdelie.contracts import DerivativeBatch, FieldBatch, ResidualBatch
from pdelie.derivatives import compute_spectral_fd_derivatives
from pdelie.errors import SchemaValidationError
from pdelie.residuals.base import ResidualEvaluator


class BurgersResidualEvaluator(ResidualEvaluator):
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

        for name in ("u_t", "u_x", "u_xx"):
            if name not in derivatives.derivatives:
                raise SchemaValidationError(f"BurgersResidualEvaluator requires derivative '{name}'.")

        diffusivity = self.diffusivity
        if diffusivity is None:
            parameter_tags = field.metadata.get("parameter_tags")
            if not isinstance(parameter_tags, dict):
                raise SchemaValidationError(
                    "BurgersResidualEvaluator requires field.metadata['parameter_tags']['nu'] when diffusivity is not provided."
                )
            nu = parameter_tags.get("nu")
            if nu is None:
                raise SchemaValidationError(
                    "BurgersResidualEvaluator requires field.metadata['parameter_tags']['nu'] when diffusivity is not provided."
                )
            try:
                diffusivity = float(nu)
            except (TypeError, ValueError) as exc:
                raise SchemaValidationError(
                    "BurgersResidualEvaluator requires field.metadata['parameter_tags']['nu'] to be castable to float."
                ) from exc

        u = np.asarray(field.values, dtype=float)
        residual = derivatives.derivatives["u_t"] + u * derivatives.derivatives["u_x"] - diffusivity * derivatives.derivatives["u_xx"]
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
