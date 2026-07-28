"""v0.34a variable-coefficient residual evaluators.

Three things here came from measurement rather than the plan.

**The equation form must be dispatched, not assumed.** The plan's stated formula
``u_t + u u_x - nu(x) u_xx`` is the *non-conservative* one, but the v0.33d
generators default to *conservative divergence* form. Measured on Heat with the
frozen sinusoidal profile, evaluating the wrong operator against matched data
inflates the residual L2 by roughly 300x, so shipping the plan's formula alone
would have mismatched default-generated data by that factor.

**A bare 1-D coefficient array broadcasts wrongly and silently.** ``FieldBatch``
values are ``(batch, time, x, var)``; multiplying by a ``(num_points,)`` array
aligns from the right and yields ``(batch, time, x, x)`` with no exception. The
result is finite and plausible-looking. This cost two invalid measurements during
the prototype before it was caught.

**A coefficient/provenance mismatch is reported, not refused.** An earlier draft
raised on "scalar coefficient, array-profile field" as a configuration error --
which broke the released v0.33d admissibility crash test, whose entire premise is
running a constant-coefficient model against variable-coefficient data.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from pdelie.data import (
    generate_advection_diffusion_1d_field_batch,
    generate_burgers_1d_field_batch,
    generate_heat_1d_field_batch,
)
from pdelie.data.heat_1d import DEFAULT_DOMAIN_LENGTH
from pdelie.errors import ScopeValidationError, ShapeValidationError
from pdelie.residuals import (
    AdvectionDiffusionResidualEvaluator,
    BurgersResidualEvaluator,
    HeatResidualEvaluator,
)
from pdelie.residuals._variable_coefficient import broadcast_coefficient_over_x

_NUM_POINTS = 64
_SEED = 0
_FORMS = ("conservative_divergence", "nonconservative_nu_uxx")


def _x_grid() -> np.ndarray:
    return np.linspace(0.0, DEFAULT_DOMAIN_LENGTH, _NUM_POINTS, endpoint=False, dtype=float)


def _profile(base: float, amplitude: float = 0.5) -> np.ndarray:
    x = _x_grid()
    return base * (1.0 + amplitude * np.sin(2.0 * np.pi * x / DEFAULT_DOMAIN_LENGTH))


# (label, generator, kwargs, base coefficient, evaluator factory taking the coefficient)
_PDE_CASES = [
    (
        "heat_1d",
        generate_heat_1d_field_batch,
        {"batch_size": 1, "num_times": 17, "num_points": _NUM_POINTS, "seed": _SEED},
        0.1,
        lambda nu: HeatResidualEvaluator(diffusivity=nu),
    ),
    (
        "burgers_1d",
        generate_burgers_1d_field_batch,
        {"batch_size": 1, "num_times": 33, "num_points": _NUM_POINTS, "seed": _SEED},
        0.1,
        lambda nu: BurgersResidualEvaluator(diffusivity=nu),
    ),
    (
        "advection_diffusion_1d",
        generate_advection_diffusion_1d_field_batch,
        {"batch_size": 1, "num_times": 65, "num_points": _NUM_POINTS, "seed": _SEED},
        0.05,
        lambda nu: AdvectionDiffusionResidualEvaluator(advection_speed=0.75, diffusivity=nu),
    ),
]
_PDE_IDS = [case[0] for case in _PDE_CASES]


def _l2(batch) -> float:
    return float(np.linalg.norm(batch.residual))


# --------------------------------------------------------------------------
# Constant path: byte-preserved
# --------------------------------------------------------------------------


@pytest.mark.parametrize(("label", "generator", "kwargs", "base", "make"), _PDE_CASES, ids=_PDE_IDS)
def test_scalar_and_constant_array_agree_to_rtol_1e_8(label, generator, kwargs, base, make) -> None:
    """The amendment-1 gate.

    A constant-valued array must reproduce the scalar path. Absolute pinning of
    the scalar path lives in the v0.33e golden gate, which runs in the release
    gate and passes unchanged.
    """
    field = generator(**kwargs)
    scalar = make(base).evaluate(field).residual
    constant_array = make(np.full(_NUM_POINTS, base)).evaluate(field).residual

    reference = float(np.linalg.norm(scalar))
    assert float(np.linalg.norm(constant_array - scalar)) / reference <= 1e-8


@pytest.mark.parametrize(("label", "generator", "kwargs", "base", "make"), _PDE_CASES, ids=_PDE_IDS)
def test_constant_path_reports_constant_dispatch(label, generator, kwargs, base, make) -> None:
    diagnostics = make(base).evaluate(generator(**kwargs)).diagnostics
    assert diagnostics["variable_coefficient_evaluator_dispatch"] == "constant"
    assert diagnostics["coefficient_matches_field_provenance"] is True
    assert diagnostics["nu"] == pytest.approx(base)


def test_both_forms_agree_when_the_coefficient_is_constant() -> None:
    """``d/dx(nu_0 du/dx)`` and ``nu_0 u_xx`` are the same operator for constant nu.

    If they ever diverge, the conservative branch has a defect the variable-path
    tests would not localize.
    """
    field = generate_heat_1d_field_batch(
        batch_size=1, num_times=17, num_points=_NUM_POINTS, seed=_SEED
    )
    constant = np.full(_NUM_POINTS, 0.1)
    residuals = {}
    for form in _FORMS:
        tagged = generate_heat_1d_field_batch(
            batch_size=1, num_times=17, num_points=_NUM_POINTS, seed=_SEED,
            diffusivity_profile=constant, diffusivity_form=form,
        )
        residuals[form] = HeatResidualEvaluator(diffusivity=constant).evaluate(tagged).residual

    reference = float(np.linalg.norm(HeatResidualEvaluator(diffusivity=0.1).evaluate(field).residual))
    difference = float(
        np.linalg.norm(residuals[_FORMS[0]] - residuals[_FORMS[1]])
    )
    assert difference / reference <= 1e-8


# --------------------------------------------------------------------------
# Array path: the form must match the generator
# --------------------------------------------------------------------------


@pytest.mark.parametrize(("label", "generator", "kwargs", "base", "make"), _PDE_CASES, ids=_PDE_IDS)
@pytest.mark.parametrize("form", _FORMS)
def test_matched_form_gives_a_small_residual(label, generator, kwargs, base, make, form) -> None:
    """Evaluating the operator the data was generated with must nearly vanish."""
    field = generator(**kwargs, diffusivity_profile=_profile(base), diffusivity_form=form)
    batch = make(_profile(base)).evaluate(field)

    assert batch.diagnostics["variable_coefficient_evaluator_dispatch"] == "array"
    assert batch.diagnostics["nu_form"] == form
    # Residual is dominated by discretization error, not by an operator mismatch.
    assert _l2(batch) < 1e-2


def test_mismatched_form_is_measurably_worse() -> None:
    """The measurement that makes ``nu_form`` a hard input rather than a label.

    Data generated one way and evaluated the other inflates the residual by
    roughly two orders of magnitude, which is why the evaluator dispatches on the
    recorded form instead of assuming one.
    """
    base = 0.1
    profile = _profile(base)
    kwargs = {"batch_size": 1, "num_times": 17, "num_points": _NUM_POINTS, "seed": _SEED}

    matched, mismatched = {}, {}
    for generated in _FORMS:
        field = generate_heat_1d_field_batch(
            **kwargs, diffusivity_profile=profile, diffusivity_form=generated
        )
        matched[generated] = _l2(HeatResidualEvaluator(diffusivity=profile).evaluate(field))
        other = _FORMS[1] if generated == _FORMS[0] else _FORMS[0]
        # Re-tag the field so the evaluator dispatches on the *other* operator.
        retagged = generate_heat_1d_field_batch(
            **kwargs, diffusivity_profile=profile, diffusivity_form=generated
        )
        retagged.metadata["parameter_tags"] = {
            **retagged.metadata["parameter_tags"], "nu_form": other
        }
        mismatched[generated] = _l2(
            HeatResidualEvaluator(diffusivity=profile).evaluate(retagged)
        )

    for generated in _FORMS:
        assert mismatched[generated] > 50.0 * matched[generated], (
            f"{generated}: matched={matched[generated]:.3e} "
            f"mismatched={mismatched[generated]:.3e}"
        )


@pytest.mark.parametrize(("label", "generator", "kwargs", "base", "make"), _PDE_CASES, ids=_PDE_IDS)
def test_constant_coefficient_on_variable_data_fails_measurably(
    label, generator, kwargs, base, make
) -> None:
    """The v0.34b crash-test signal, computed through the v0.34a array path.

    Far exceeds the 10x threshold v0.34b will assert: measured 711x (Heat),
    10274x (Burgers), 1575x (advection-diffusion) on the conservative form.
    """
    field = generator(**kwargs, diffusivity_profile=_profile(base))
    matched = _l2(make(_profile(base)).evaluate(field))
    constant = _l2(make(base).evaluate(field))

    assert constant >= 10.0 * matched


# --------------------------------------------------------------------------
# The silent-broadcast trap
# --------------------------------------------------------------------------


def test_bare_one_dimensional_array_would_broadcast_over_the_wrong_axis() -> None:
    """Pin the hazard the helper exists to prevent.

    NumPy aligns from the right, so a ``(n_x,)`` coefficient multiplied against a
    ``(batch, time, x, var)`` derivative broadcasts against ``var`` and silently
    produces a ``(batch, time, x, x)`` array. No exception; the residual is
    finite and wrong.
    """
    coefficient = np.ones(_NUM_POINTS)
    derivative = np.ones((1, 17, _NUM_POINTS, 1))

    assert (coefficient * derivative).shape == (1, 17, _NUM_POINTS, _NUM_POINTS)

    field = generate_heat_1d_field_batch(
        batch_size=1, num_times=17, num_points=_NUM_POINTS, seed=_SEED
    )
    reshaped = broadcast_coefficient_over_x(
        coefficient, field=field, name="probe"
    )
    assert (reshaped * derivative).shape == derivative.shape


def test_broadcast_helper_passes_scalars_through() -> None:
    field = generate_heat_1d_field_batch(
        batch_size=1, num_times=17, num_points=_NUM_POINTS, seed=_SEED
    )
    assert broadcast_coefficient_over_x(0.25, field=field, name="probe") == 0.25


@pytest.mark.parametrize(
    "bad", [np.ones(_NUM_POINTS + 3), np.ones((2, _NUM_POINTS)), np.ones(1)],
    ids=["too-long", "two-dimensional", "too-short"],
)
def test_wrong_shaped_coefficient_is_rejected(bad) -> None:
    field = generate_heat_1d_field_batch(
        batch_size=1, num_times=17, num_points=_NUM_POINTS, seed=_SEED
    )
    with pytest.raises(ShapeValidationError, match="one value per spatial grid point"):
        broadcast_coefficient_over_x(bad, field=field, name="probe")


# --------------------------------------------------------------------------
# Rejections and reports
# --------------------------------------------------------------------------


@pytest.mark.parametrize("bad", [np.full(_NUM_POINTS, np.nan), np.full(_NUM_POINTS, np.inf)],
                         ids=["nan", "inf"])
def test_non_finite_coefficient_array_is_rejected(bad) -> None:
    field = generate_heat_1d_field_batch(
        batch_size=1, num_times=17, num_points=_NUM_POINTS, seed=_SEED,
        diffusivity_profile=_profile(0.1),
    )
    with pytest.raises(ScopeValidationError, match="finite"):
        HeatResidualEvaluator(diffusivity=bad).evaluate(field)


def test_callable_profile_field_is_rejected_with_a_pointer_to_pre_sampling() -> None:
    field = generate_heat_1d_field_batch(
        batch_size=1, num_times=17, num_points=_NUM_POINTS, seed=_SEED,
        diffusivity_profile=lambda x: 0.1 * (1.0 + 0.5 * np.sin(2.0 * np.pi * x / DEFAULT_DOMAIN_LENGTH)),
    )
    with pytest.raises(ScopeValidationError, match="pre-sampled"):
        HeatResidualEvaluator(diffusivity=_profile(0.1)).evaluate(field)


def test_coefficient_provenance_mismatch_is_reported_not_refused() -> None:
    """Refusing this would break the released v0.33d admissibility crash test."""
    field = generate_heat_1d_field_batch(
        batch_size=1, num_times=17, num_points=_NUM_POINTS, seed=_SEED,
        diffusivity_profile=_profile(0.1),
    )
    batch = HeatResidualEvaluator(diffusivity=0.1).evaluate(field)

    assert batch.diagnostics["coefficient_matches_field_provenance"] is False
    assert np.all(np.isfinite(batch.residual))


def test_conservative_advection_form_is_refused_rather_than_mis_evaluated() -> None:
    """v0.33d can generate conservative advection; v0.34a does not evaluate it.

    Silently applying the non-conservative advective operator to conservatively
    generated data would produce a wrong residual with no signal.
    """
    field = generate_advection_diffusion_1d_field_batch(
        batch_size=1, num_times=65, num_points=_NUM_POINTS, seed=_SEED,
        advection_profile=_profile(0.75),
        advection_form="conservative_divergence",
    )
    with pytest.raises(ScopeValidationError, match="non-conservative advective"):
        AdvectionDiffusionResidualEvaluator(diffusivity=0.05).evaluate(field)


# --------------------------------------------------------------------------
# Diagnostics surface
# --------------------------------------------------------------------------


@pytest.mark.parametrize(("label", "generator", "kwargs", "base", "make"), _PDE_CASES, ids=_PDE_IDS)
def test_array_path_diagnostics_are_complete_and_strict_json(
    label, generator, kwargs, base, make
) -> None:
    field = generator(**kwargs, diffusivity_profile=_profile(base))
    diagnostics = make(_profile(base)).evaluate(field).diagnostics

    assert diagnostics["variable_coefficient_evaluator_dispatch"] == "array"
    assert diagnostics["nu_form"] in _FORMS
    assert diagnostics["coefficient_matches_field_provenance"] is True
    for key in ("nu_min", "nu_max", "nu_l2_norm"):
        assert isinstance(diagnostics[key], float)

    assert json.loads(json.dumps(diagnostics, allow_nan=False)) == diagnostics


@pytest.mark.parametrize(("label", "generator", "kwargs", "base", "make"), _PDE_CASES, ids=_PDE_IDS)
def test_residual_batch_shape_is_unchanged_on_the_array_path(
    label, generator, kwargs, base, make
) -> None:
    """The array path must not alter the ResidualBatch top-level shape."""
    field = generator(**kwargs, diffusivity_profile=_profile(base))
    batch = make(_profile(base)).evaluate(field)

    assert batch.residual.shape == field.values.shape
    assert batch.definition_type == "analytic"
    assert batch.normalization == "none"


def test_interior_only_policy_still_applies_on_nonperiodic_variable_data() -> None:
    """Variable coefficients are orthogonal to the boundary-condition dispatch."""
    from pdelie.contracts import FieldBatch

    periodic = generate_heat_1d_field_batch(
        batch_size=1, num_times=17, num_points=128, seed=_SEED,
        diffusivity_profile=0.1 * (
            1.0
            + 0.5
            * np.sin(
                2.0
                * np.pi
                * np.linspace(0.0, DEFAULT_DOMAIN_LENGTH, 128, endpoint=False)
                / DEFAULT_DOMAIN_LENGTH
            )
        ),
    )
    width = int(128 * 0.6)
    low = (128 - width) // 2
    metadata = dict(periodic.metadata)
    metadata["boundary_conditions"] = {"x": "dirichlet"}
    cropped = FieldBatch(
        values=periodic.values[:, :, low : low + width, :].copy(),
        dims=periodic.dims,
        coords={
            "time": periodic.coords["time"].copy(),
            "x": periodic.coords["x"][low : low + width].copy(),
        },
        var_names=list(periodic.var_names),
        metadata=metadata,
        preprocess_log=[],
    )
    profile = np.asarray(
        0.1
        * (
            1.0
            + 0.5 * np.sin(2.0 * np.pi * cropped.coords["x"] / DEFAULT_DOMAIN_LENGTH)
        ),
        dtype=float,
    )
    diagnostics = HeatResidualEvaluator(diffusivity=profile).evaluate(cropped).diagnostics

    assert diagnostics["backend"] == "finite_difference"
    assert diagnostics["residual_domain_policy"] == "interior_only"
    assert diagnostics["variable_coefficient_evaluator_dispatch"] == "array"
