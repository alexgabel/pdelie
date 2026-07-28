from __future__ import annotations

from collections.abc import Mapping

import numpy as np

from pdelie.contracts import DerivativeBatch, FieldBatch, ResidualBatch
from pdelie.data._coefficient_profiles import (
    ADVECTION_FORM_NONCONSERVATIVE,
    ALLOWED_ADVECTION_FORMS,
)
from pdelie.data.advection_diffusion_1d import DEFAULT_ADVECTION_DIFFUSION_EQUATION
from pdelie.derivatives import compute_derivatives
from pdelie.errors import SchemaValidationError, ScopeValidationError
from pdelie.residuals._variable_coefficient import (
    apply_diffusion_operator,
    resolve_variable_coefficient,
    variable_coefficient_diagnostics,
)
from pdelie.residuals.base import (
    ResidualEvaluator,
    build_residual_diagnostics_from_derivatives,
)

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

    # v0.30d: BC gate deferred to the derivative backend via compute_derivatives(backend="auto").
    # Periodic data routes to spectral_fd; supported nonperiodic BCs (dirichlet, neumann,
    # open_unknown) route to finite_difference and receive interior-only residual diagnostics.

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
    def __init__(
        self,
        *,
        advection_speed: float | np.ndarray | None = None,
        diffusivity: float | np.ndarray | None = None,
    ) -> None:
        """v0.34a: both coefficients accept a scalar or a pre-sampled array.

        Array coefficients skip the scalar finiteness/positivity helpers, which
        cannot express an elementwise check; the array path validates finiteness
        in ``resolve_variable_coefficient`` instead. The diffusive term follows
        ``parameter_tags["nu_form"]`` and the advective term
        ``parameter_tags["c_form"]``.
        """
        self.advection_speed = (
            advection_speed
            if advection_speed is None or np.ndim(advection_speed) > 0
            else _finite_parameter(advection_speed, name="advection_speed")
        )
        self.diffusivity = (
            diffusivity
            if diffusivity is None or np.ndim(diffusivity) > 0
            else _finite_positive_parameter(diffusivity, name="diffusivity")
        )

    def evaluate(
        self,
        field: FieldBatch,
        derivatives: DerivativeBatch | None = None,
    ) -> ResidualBatch:
        parameter_tags = _validate_advection_diffusion_field(field)
        if self.advection_speed is None:
            _finite_parameter(parameter_tags.get("c"), name="field.metadata['parameter_tags']['c']")
        if self.diffusivity is None:
            _finite_positive_parameter(
                parameter_tags.get("nu"), name="field.metadata['parameter_tags']['nu']"
            )

        if derivatives is None:
            derivatives = compute_derivatives(field, backend="auto")
        derivatives.validate_against(field)

        for name in _REQUIRED_DERIVATIVES:
            if name not in derivatives.derivatives:
                raise SchemaValidationError(f"AdvectionDiffusionResidualEvaluator requires derivative '{name}'.")

        diffusivity, nu_dispatch, nu_form, nu_matches = resolve_variable_coefficient(
            self.diffusivity,
            field=field,
            parameter_tag="nu",
            kind_tag="nu_profile_kind",
            form_tag="nu_form",
            name="AdvectionDiffusionResidualEvaluator diffusivity",
        )
        advection_speed, c_dispatch, c_form, c_matches = resolve_variable_coefficient(
            self.advection_speed,
            field=field,
            parameter_tag="c",
            kind_tag="c_profile_kind",
            form_tag="c_form",
            name="AdvectionDiffusionResidualEvaluator advection_speed",
            allowed_forms=ALLOWED_ADVECTION_FORMS,
            default_form=ADVECTION_FORM_NONCONSERVATIVE,
        )

        # The advective term is non-conservative in both the constant and array
        # cases, matching the v0.33d generator default (c_form
        # "nonconservative_c_ux"). The conservative advective form -d/dx(c(x) u)
        # is generated by v0.33d but is NOT yet evaluated here; a field carrying
        # c_form="conservative_divergence" is refused rather than silently
        # evaluated under the wrong operator.
        if c_form != "nonconservative_c_ux":
            raise ScopeValidationError(
                "AdvectionDiffusionResidualEvaluator evaluates the non-conservative "
                f"advective term only; this field records c_form={c_form!r}. "
                "Conservative advection is deferred to a later milestone; "
                "regenerate with advection_form='nonconservative_c_ux'."
            )

        if nu_dispatch == "constant" and c_dispatch == "constant":
            # Byte-preserved scalar path: the identical expression to pre-v0.34a.
            residual = (
                derivatives.derivatives["u_t"]
                + advection_speed * derivatives.derivatives["u_x"]
                - diffusivity * derivatives.derivatives["u_xx"]
            )
        else:
            residual = (
                derivatives.derivatives["u_t"]
                + advection_speed * derivatives.derivatives["u_x"]
                - apply_diffusion_operator(
                    diffusivity, field=field, derivatives=derivatives, form=nu_form
                )
            )
        batch = ResidualBatch(
            residual=residual,
            definition_type="analytic",
            normalization="none",
            diagnostics=build_residual_diagnostics_from_derivatives(
                residual,
                field,
                derivatives,
                extra={
                    "equation": _ADVECTION_DIFFUSION_EQUATION,
                    "c": float(advection_speed) if c_dispatch == "constant" else None,
                    "nu": float(diffusivity) if nu_dispatch == "constant" else None,
                    **variable_coefficient_diagnostics(
                        dispatch=nu_dispatch,
                        form=nu_form,
                        field=field,
                        prefix="nu",
                        matches_provenance=nu_matches and c_matches,
                    ),
                    "c_form": c_form,
                    "advection_coefficient_dispatch": c_dispatch,
                },
            ),
        )
        batch.validate_against(field)
        return batch
