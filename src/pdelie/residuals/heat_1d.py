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

#: Derivatives every heat residual needs, on any coefficient path.
#:
#: ``u_x`` is deliberately absent. It is required only on the
#: variable-coefficient path -- where the product rule introduces a
#: ``nu'(x) u_x`` term -- and that requirement is raised at the point of use.
#: Adding it here would demand it on the constant-coefficient path, which does
#: not need it.
_REQUIRED_DERIVATIVES: tuple[str, ...] = ("u_t", "u_xx")


class HeatResidualEvaluator(ResidualEvaluator):
    """``u_t - (diffusive term) = 0``.

    ``diffusivity`` accepts a scalar, a pre-sampled ``(num_points,)`` array
    (v0.34a), or ``None`` to read ``parameter_tags["nu"]`` from the field.

    On the array path the diffusive term is whichever operator the v0.33d
    generator recorded in ``parameter_tags["nu_form"]`` --
    ``d/dx(nu(x) du/dx)`` or ``nu(x) * u_xx``. These are different operators for
    any non-constant ``nu``: measured on the frozen sinusoidal profile,
    evaluating the wrong one against matched data inflates the residual L2 by
    roughly 300x. They coincide for constant ``nu``, so the scalar path is
    unaffected by the choice and is byte-preserved from pre-v0.34a.

    Callable profiles are refused; pass the array the generator sampled.
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
                raise SchemaValidationError(f"HeatResidualEvaluator requires derivative '{name}'.")

        coefficient, dispatch, form, matches_provenance = resolve_variable_coefficient(
            self.diffusivity,
            field=field,
            parameter_tag="nu",
            kind_tag="nu_profile_kind",
            form_tag="nu_form",
            name="HeatResidualEvaluator diffusivity",
        )

        if dispatch == "constant":
            # Byte-preserved scalar path: the identical expression to pre-v0.34a.
            residual = (
                derivatives.derivatives["u_t"] - coefficient * derivatives.derivatives["u_xx"]
            )
        else:
            if "u_x" not in derivatives.derivatives:
                raise SchemaValidationError(
                    "HeatResidualEvaluator requires derivative 'u_x' on the "
                    "variable-coefficient path."
                )
            residual = derivatives.derivatives["u_t"] - apply_diffusion_operator(
                coefficient, field=field, derivatives=derivatives, form=form
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
