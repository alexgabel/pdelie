from __future__ import annotations

from collections.abc import Mapping

import numpy as np

from pdelie._boundary import is_x_periodic
from pdelie.contracts import DerivativeBatch, FieldBatch, ResidualBatch
from pdelie.data.reaction_diffusion_1d import DEFAULT_REACTION_DIFFUSION_EQUATION
from pdelie.derivatives import compute_spectral_fd_derivatives
from pdelie.errors import SchemaValidationError, ScopeValidationError
from pdelie.residuals.base import ResidualEvaluator


_REACTION_DIFFUSION_EQUATION = "u_t - nu*u_xx - rho*u*(1-u) = 0"
_REQUIRED_DERIVATIVES = ("u_t", "u_xx")


def _finite_positive_parameter(value: object, *, name: str) -> float:
    if isinstance(value, (bool, np.bool_)):
        raise SchemaValidationError(f"{name} must be a finite positive scalar.")
    try:
        normalized = float(value)
    except (TypeError, ValueError) as exc:
        raise SchemaValidationError(f"{name} must be a finite positive scalar.") from exc
    if not np.isfinite(normalized) or normalized <= 0.0:
        raise SchemaValidationError(f"{name} must be a finite positive scalar.")
    return normalized


def _validate_reaction_diffusion_field(field: FieldBatch) -> Mapping[str, object]:
    field.validate()

    if field.dims != ("batch", "time", "x", "var"):
        raise ScopeValidationError(
            "ReactionDiffusionResidualEvaluator only supports dims ('batch', 'time', 'x', 'var')."
        )
    if len(field.var_names) != 1 or field.values.shape[-1] != 1:
        raise ScopeValidationError("ReactionDiffusionResidualEvaluator only supports scalar FieldBatch inputs.")
    if field.mask is not None:
        raise ScopeValidationError("ReactionDiffusionResidualEvaluator does not support masked fields.")
    if not np.all(np.isfinite(field.values)):
        raise ScopeValidationError("ReactionDiffusionResidualEvaluator requires finite field values.")

    if not is_x_periodic(field):
        raise ScopeValidationError("ReactionDiffusionResidualEvaluator requires periodic boundary conditions in x.")

    parameter_tags = field.metadata.get("parameter_tags")
    if not isinstance(parameter_tags, Mapping):
        raise SchemaValidationError(
            "ReactionDiffusionResidualEvaluator requires field.metadata['parameter_tags'] to be a mapping."
        )
    if parameter_tags.get("equation") != DEFAULT_REACTION_DIFFUSION_EQUATION:
        raise ScopeValidationError(
            "ReactionDiffusionResidualEvaluator requires "
            "field.metadata['parameter_tags']['equation'] == 'reaction_diffusion_fisher_kpp'."
        )
    return parameter_tags


class ReactionDiffusionResidualEvaluator(ResidualEvaluator):
    def __init__(self, *, diffusivity: float | None = None, reaction_rate: float | None = None) -> None:
        self.diffusivity = None if diffusivity is None else _finite_positive_parameter(diffusivity, name="diffusivity")
        self.reaction_rate = (
            None if reaction_rate is None else _finite_positive_parameter(reaction_rate, name="reaction_rate")
        )

    def evaluate(
        self,
        field: FieldBatch,
        derivatives: DerivativeBatch | None = None,
    ) -> ResidualBatch:
        parameter_tags = _validate_reaction_diffusion_field(field)
        diffusivity = (
            _finite_positive_parameter(parameter_tags.get("nu"), name="field.metadata['parameter_tags']['nu']")
            if self.diffusivity is None
            else self.diffusivity
        )
        reaction_rate = (
            _finite_positive_parameter(parameter_tags.get("rho"), name="field.metadata['parameter_tags']['rho']")
            if self.reaction_rate is None
            else self.reaction_rate
        )

        if derivatives is None:
            derivatives = compute_spectral_fd_derivatives(field)
        derivatives.validate_against(field)

        for name in _REQUIRED_DERIVATIVES:
            if name not in derivatives.derivatives:
                raise SchemaValidationError(f"ReactionDiffusionResidualEvaluator requires derivative '{name}'.")

        u = np.asarray(field.values, dtype=float)
        residual = (
            derivatives.derivatives["u_t"]
            - diffusivity * derivatives.derivatives["u_xx"]
            - reaction_rate * u * (1.0 - u)
        )
        batch = ResidualBatch(
            residual=residual,
            definition_type="analytic",
            normalization="none",
            diagnostics={
                "backend": derivatives.backend,
                "equation": _REACTION_DIFFUSION_EQUATION,
                "nu": diffusivity,
                "rho": reaction_rate,
                "max_abs_residual": float(np.max(np.abs(residual))),
                "rms_residual": float(np.sqrt(np.mean(np.square(residual)))),
            },
        )
        batch.validate_against(field)
        return batch
