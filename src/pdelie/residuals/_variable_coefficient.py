"""v0.34a: shared variable-coefficient machinery for the residual evaluators.

Two measured facts shape this module.

**The equation form is not optional.** ``d/dx(nu(x) du/dx)`` and ``nu(x)*u_xx``
are different operators for any non-constant ``nu``. Measured on Heat with
``nu(x) = nu_0 (1 + 0.5 sin(2 pi x / L))``, evaluating the wrong one against
matched data inflates the residual L2 by roughly 300x::

    data generated as        residual assumes         residual L2
    conservative_divergence  conservative_divergence   2.31e-03   <- matched
    conservative_divergence  nonconservative_nu_uxx    6.79e-01
    nonconservative_nu_uxx   conservative_divergence   6.77e-01
    nonconservative_nu_uxx   nonconservative_nu_uxx    1.93e-03   <- matched

The v0.33d generators record which operator produced the data in
``parameter_tags["nu_form"]``, and the evaluators dispatch on it rather than
assuming.

A coefficient whose *kind* disagrees with the field's recorded
``nu_profile_kind`` is **reported, never refused**: the resolved tuple carries
``matches_provenance`` and the residual diagnostics carry
``coefficient_matches_field_provenance``. Refusing the mismatch would break the
v0.33d admissibility crash test, whose entire premise is running a
constant-coefficient model against variable-coefficient data and observing it
fail measurably. An earlier draft of this module did refuse it and broke that
released behaviour.

**A bare 1-D coefficient array broadcasts wrongly and silently.** ``FieldBatch``
values are ``(batch, time, x, var)``. Multiplying by a ``(num_points,)`` array
aligns from the right, so it broadcasts against the ``var`` axis and yields a
``(batch, time, x, x)`` array with no exception raised -- the resulting residual
is finite, plausible-looking, and wrong. :func:`broadcast_coefficient_over_x`
exists so no evaluator writes that multiplication by hand.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from pdelie.contracts import DerivativeBatch, FieldBatch
from pdelie.data._coefficient_profiles import (
    ALLOWED_DIFFUSIVITY_FORMS,
    DIFFUSIVITY_FORM_CONSERVATIVE,
    DIFFUSIVITY_FORM_NONCONSERVATIVE,
)
from pdelie.derivatives import compute_derivatives
from pdelie.errors import ScopeValidationError, ShapeValidationError

__all__ = [
    "broadcast_coefficient_over_x",
    "differentiate_along_x",
    "resolve_variable_coefficient",
    "variable_coefficient_diagnostics",
]

_X_AXIS = 2


def broadcast_coefficient_over_x(
    coefficient: float | np.ndarray, *, field: FieldBatch, name: str
) -> np.ndarray | float:
    """Shape a coefficient so it multiplies along the **x** axis.

    A scalar is returned unchanged. A 1-D array is reshaped to ``(1, 1, n_x, 1)``
    so it aligns with the x axis of ``(batch, time, x, var)`` values.

    Never multiply a raw ``(n_x,)`` array against a derivative array directly:
    NumPy aligns from the right, so it would broadcast against ``var`` and
    produce a ``(batch, time, x, x)`` result without raising.
    """
    if np.ndim(coefficient) == 0:
        return float(coefficient)

    values = np.asarray(coefficient, dtype=float)
    expected = int(field.values.shape[_X_AXIS])
    if values.ndim != 1 or values.size != expected:
        raise ShapeValidationError(
            f"{name} must be one-dimensional with one value per spatial grid point "
            f"({expected},); got shape {values.shape}. A coefficient of any other "
            "shape cannot be aligned with the x axis of a "
            "(batch, time, x, var) FieldBatch."
        )
    return values.reshape(1, 1, -1, 1)


def differentiate_along_x(
    values: np.ndarray, *, field: FieldBatch
) -> np.ndarray:
    """First x-derivative of an arbitrary ``(batch, time, x, var)`` array.

    Routed through :func:`compute_derivatives` on a temporary ``FieldBatch`` so
    the derivative uses exactly the same backend the residual's own derivatives
    used -- spectral for periodic data, finite-difference for nonperiodic. Doing
    the differentiation inline with a hand-rolled FFT would silently apply a
    periodic operator to nonperiodic data.
    """
    carrier = FieldBatch(
        values=np.asarray(values, dtype=float),
        dims=field.dims,
        coords={name: coord.copy() for name, coord in field.coords.items()},
        var_names=list(field.var_names),
        metadata=dict(field.metadata),
        preprocess_log=[],
    )
    return np.asarray(
        compute_derivatives(carrier, backend="auto").derivatives["u_x"], dtype=float
    )


def resolve_variable_coefficient(
    coefficient: float | np.ndarray | None,
    *,
    field: FieldBatch,
    parameter_tag: str,
    kind_tag: str,
    form_tag: str,
    name: str,
    allowed_forms: frozenset[str] = ALLOWED_DIFFUSIVITY_FORMS,
    default_form: str = DIFFUSIVITY_FORM_CONSERVATIVE,
) -> tuple[np.ndarray | float, str, str, bool]:
    """Resolve a coefficient and the equation form to evaluate it under.

    Returns ``(broadcast_coefficient, dispatch, form, matches_provenance)`` where
    ``dispatch`` is ``"constant"`` or ``"array"`` and ``matches_provenance`` says
    whether the caller's coefficient kind agrees with the field's recorded
    ``nu_profile_kind``. A mismatch is reported, not refused: the v0.33d
    admissibility crash test *depends* on evaluating variable-coefficient data
    with a constant coefficient.

    A ``callable`` profile is refused: the v0.33d generators sample callables
    once at generation time and record the sampled array's provenance, so a
    residual evaluator receiving a callable would be re-sampling on a grid it
    cannot verify matches the one the data was generated on.
    """
    tags = field.metadata.get("parameter_tags", {})
    profile_kind = tags.get(kind_tag, "constant")
    # Fields predating v0.33d carry no form tag; fall back to this
    # coefficient's own default rather than the diffusivity one.
    form = tags.get(form_tag, default_form)

    if profile_kind == "callable":
        raise ScopeValidationError(
            f"{name}: this field's {kind_tag} is 'callable'. Residual evaluators "
            "consume pre-sampled coefficient arrays only. Regenerate the field "
            "with the v0.33d data generator, which samples the callable once on "
            "its own x grid and records the sampled array's provenance, then pass "
            "that array."
        )

    if form not in allowed_forms:
        raise ScopeValidationError(
            f"{name}: unsupported {form_tag} {form!r}; expected one of "
            f"{sorted(allowed_forms)}."
        )

    if coefficient is None:
        coefficient = float(tags[parameter_tag])

    is_array = np.ndim(coefficient) > 0

    if is_array:
        values = np.asarray(coefficient, dtype=float)
        if not np.all(np.isfinite(values)):
            raise ScopeValidationError(f"{name} must be finite everywhere.")

    # A coefficient that disagrees with the field's own provenance is REPORTED,
    # never refused. Evaluating variable-coefficient data with a constant
    # coefficient is precisely the v0.33d admissibility crash test -- the whole
    # point is that a constant-coefficient model runs to completion on
    # variable-coefficient data and fails measurably. Refusing the combination
    # would make that diagnostic impossible to compute.
    coefficient_matches_field_provenance = is_array == (profile_kind == "array")

    return (
        broadcast_coefficient_over_x(coefficient, field=field, name=name),
        "array" if is_array else "constant",
        form,
        coefficient_matches_field_provenance,
    )


def apply_diffusion_operator(
    coefficient: np.ndarray | float,
    *,
    field: FieldBatch,
    derivatives: DerivativeBatch,
    form: str,
) -> np.ndarray:
    """Evaluate the diffusive term under the recorded equation form."""
    if form == DIFFUSIVITY_FORM_NONCONSERVATIVE:
        return np.asarray(
            coefficient * derivatives.derivatives["u_xx"], dtype=float
        )
    flux = coefficient * derivatives.derivatives["u_x"]
    return differentiate_along_x(flux, field=field)


def variable_coefficient_diagnostics(
    *,
    dispatch: str,
    form: str,
    field: FieldBatch,
    prefix: str,
    matches_provenance: bool = True,
) -> dict[str, Any]:
    """Additive diagnostics forwarded onto ``ResidualBatch.diagnostics``.

    The magnitude tags are forwarded from the field's own ``parameter_tags`` so
    downstream consumers read one uniform surface regardless of whether the
    coefficient was constant or an array.
    """
    tags = field.metadata.get("parameter_tags", {})
    payload: dict[str, Any] = {
        "variable_coefficient_evaluator_dispatch": dispatch,
        f"{prefix}_form": form,
        # False when the caller's coefficient kind disagrees with the field's
        # recorded profile kind. This is the signature of the admissibility
        # crash test, so it is surfaced rather than treated as an error.
        "coefficient_matches_field_provenance": bool(matches_provenance),
    }
    for suffix in ("min", "max", "l2_norm"):
        key = f"{prefix}_{suffix}"
        if key in tags:
            payload[key] = float(tags[key])
    return payload
