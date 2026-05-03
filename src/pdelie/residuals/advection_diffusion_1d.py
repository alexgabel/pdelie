from __future__ import annotations

from collections.abc import Mapping

import numpy as np

from pdelie.contracts import DerivativeBatch, FieldBatch, ResidualBatch
from pdelie.data.advection_diffusion_1d import DEFAULT_ADVECTION_DIFFUSION_EQUATION
from pdelie.derivatives import compute_spectral_fd_derivatives
from pdelie.errors import SchemaValidationError, ScopeValidationError
from pdelie.residuals.base import ResidualEvaluator


_ADVECTION_DIFFUSION_EQUATION = "u_t + c*u_x - nu*u_xx = 0"
_REQUIRED_DERIVATIVES = ("u_t", "u_x", "u_xx")


def _finite_parameter(value: object, *, name: str) -> float:
    if isinstance(value, (bool, np.bool_)):
        raise SchemaValidationError(f"{name} must be a finite scalar.")
    try:
        normalized = float(value)
    except (TypeError, ValueError) as exc:
        raise SchemaValidationError(f"{name} must be a finite scalar.") from exc
    if not np.isfinite(normalized):
        raise SchemaValidationError(f"{name} must be a finite scalar.")
    return normalized


def _finite_positive_parameter(value: object, *, name: str) -> float:
    normalized = _finite_parameter(value, name=name)
    if normalized <= 0.0:
        raise SchemaValidationError(f"{name} must be a finite positive scalar.")
    return normalized


def _validate_advection_diffusion_field(field: FieldBatch) -> Mapping[str, object]:
    field.validate()

    if field.dims != ("batch", "time", "x", "var"):
        raise ScopeValidationError(
            "AdvectionDiffusionResidualEvaluator only supports dims ('batch', 'time', 'x', 'var')."
        )
    if len(field.var_names) != 1 or field.values.shape[-1] != 1:
        raise ScopeValidationError("AdvectionDiffusionResidualEvaluator only supports scalar FieldBatch inputs.")
    if field.mask is not None:
        raise ScopeValidationError("AdvectionDiffusionResidualEvaluator does not support masked fields.")
    if not np.all(np.isfinite(field.values)):
        raise ScopeValidationError("AdvectionDiffusionResidualEvaluator requires finite field values.")

    boundary_conditions = field.metadata.get("boundary_conditions")
    if not isinstance(boundary_conditions, Mapping) or boundary_conditions.get("x") != "periodic":
        raise ScopeValidationError("AdvectionDiffusionResidualEvaluator requires periodic boundary conditions in x.")

    parameter_tags = field.metadata.get("parameter_tags")
    if not isinstance(parameter_tags, Mapping):
        raise SchemaValidationError(
            "AdvectionDiffusionResidualEvaluator requires field.metadata['parameter_tags'] to be a mapping."
        )
    if parameter_tags.get("equation") != DEFAULT_ADVECTION_DIFFUSION_EQUATION:
        raise ScopeValidationError(
            "AdvectionDiffusionResidualEvaluator requires "
            "field.metadata['parameter_tags']['equation'] == 'advection_diffusion_constant_coefficient'."
        )
    return parameter_tags


class AdvectionDiffusionResidualEvaluator(ResidualEvaluator):
    def __init__(self, *, advection_speed: float | None = None, diffusivity: float | None = None) -> None:
        self.advection_speed = (
            None if advection_speed is None else _finite_parameter(advection_speed, name="advection_speed")
        )
        self.diffusivity = None if diffusivity is None else _finite_positive_parameter(diffusivity, name="diffusivity")

    def evaluate(
        self,
        field: FieldBatch,
        derivatives: DerivativeBatch | None = None,
    ) -> ResidualBatch:
        parameter_tags = _validate_advection_diffusion_field(field)
        advection_speed = (
            _finite_parameter(parameter_tags.get("c"), name="field.metadata['parameter_tags']['c']")
            if self.advection_speed is None
            else self.advection_speed
        )
        diffusivity = (
            _finite_positive_parameter(parameter_tags.get("nu"), name="field.metadata['parameter_tags']['nu']")
            if self.diffusivity is None
            else self.diffusivity
        )

        if derivatives is None:
            derivatives = compute_spectral_fd_derivatives(field)
        derivatives.validate_against(field)

        for name in _REQUIRED_DERIVATIVES:
            if name not in derivatives.derivatives:
                raise SchemaValidationError(f"AdvectionDiffusionResidualEvaluator requires derivative '{name}'.")

        residual = (
            derivatives.derivatives["u_t"]
            + advection_speed * derivatives.derivatives["u_x"]
            - diffusivity * derivatives.derivatives["u_xx"]
        )
        batch = ResidualBatch(
            residual=residual,
            definition_type="analytic",
            normalization="none",
            diagnostics={
                "backend": derivatives.backend,
                "equation": _ADVECTION_DIFFUSION_EQUATION,
                "c": advection_speed,
                "nu": diffusivity,
                "max_abs_residual": float(np.max(np.abs(residual))),
                "rms_residual": float(np.sqrt(np.mean(np.square(residual)))),
            },
        )
        batch.validate_against(field)
        return batch
