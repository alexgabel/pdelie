from __future__ import annotations

import numpy as np

from pdelie.contracts import DerivativeBatch, FieldBatch, ResidualBatch
from pdelie.derivatives import compute_derivatives
from pdelie.errors import SchemaValidationError
from pdelie.residuals._variable_coefficient import (
    apply_diffusion_operator,
    resolve_variable_coefficient,
    variable_coefficient_diagnostics,
)
from pdelie.residuals.base import (
    ResidualEvaluator,
    build_residual_diagnostics_from_derivatives,
)

#: Derivatives every Burgers residual needs.
_REQUIRED_DERIVATIVES: tuple[str, ...] = ("u_t", "u_x", "u_xx")


class BurgersResidualEvaluator(ResidualEvaluator):
    """``u_t + u u_x - (diffusive term) = 0``.

    ``diffusivity`` accepts a scalar, a pre-sampled ``(num_points,)`` array
    (v0.34a), or ``None`` to read ``parameter_tags["nu"]``. On the array path the
    diffusive term follows ``parameter_tags["nu_form"]``; see
    :mod:`pdelie.residuals._variable_coefficient` for why the form is dispatched
    rather than assumed. The advective term ``u u_x`` is unaffected.
    """

    def __init__(self, diffusivity: float | np.ndarray | None = None) -> None:
        self.diffusivity = diffusivity

    def evaluate(
        self,
        field: FieldBatch,
        derivatives: DerivativeBatch | None = None,
    ) -> ResidualBatch:
        field.validate()
        if derivatives is None:
            derivatives = compute_derivatives(field, backend="auto")
        derivatives.validate_against(field)

        for name in _REQUIRED_DERIVATIVES:
            if name not in derivatives.derivatives:
                raise SchemaValidationError(f"BurgersResidualEvaluator requires derivative '{name}'.")

        if self.diffusivity is None:
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
                float(nu)
            except (TypeError, ValueError) as exc:
                raise SchemaValidationError(
                    "BurgersResidualEvaluator requires field.metadata['parameter_tags']['nu'] to be castable to float."
                ) from exc

        coefficient, dispatch, form, matches_provenance = resolve_variable_coefficient(
            self.diffusivity,
            field=field,
            parameter_tag="nu",
            kind_tag="nu_profile_kind",
            form_tag="nu_form",
            name="BurgersResidualEvaluator diffusivity",
        )

        u = np.asarray(field.values, dtype=float)
        advection = u * derivatives.derivatives["u_x"]
        if dispatch == "constant":
            # Byte-preserved scalar path: the identical expression to pre-v0.34a.
            residual = (
                derivatives.derivatives["u_t"]
                + advection
                - coefficient * derivatives.derivatives["u_xx"]
            )
        else:
            residual = (
                derivatives.derivatives["u_t"]
                + advection
                - apply_diffusion_operator(
                    coefficient, field=field, derivatives=derivatives, form=form
                )
            )

        extra: dict[str, object] = {
            "nu": float(coefficient) if dispatch == "constant" else None
        }
        extra.update(
            variable_coefficient_diagnostics(
                dispatch=dispatch,
                form=form,
                field=field,
                prefix="nu",
                matches_provenance=matches_provenance,
            )
        )

        batch = ResidualBatch(
            residual=residual,
            definition_type="analytic",
            normalization="none",
            diagnostics=build_residual_diagnostics_from_derivatives(
                residual, field, derivatives, extra=extra
            ),
        )
        batch.validate_against(field)
        return batch
