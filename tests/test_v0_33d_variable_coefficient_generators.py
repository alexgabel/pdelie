"""v0.33d variable-coefficient data-generator tests.

Covers the four frozen exit gates:

1. The constant path (``diffusivity_profile=None``) is byte-preserved.
2. Array and callable paths produce well-formed FieldBatches with correct
   provenance in ``metadata["parameter_tags"]``.
3. Shape mismatch, non-finite, and non-positive profiles raise typed errors
   before any numerical work.
4. The admissibility crash test: a constant-coefficient generator run against
   variable-coefficient data measurably fails.

On gate 4, the asserted metric is ``residual_l2``, **not** ``span_distance``.
``span_distance`` cannot carry this assertion: ``fit_translation_generator``
falls back to the reference translation coefficients when the SVD drifts and the
constant basis is least-sensitive, and that fallback drives ``span_distance`` to
exactly ``0.0`` -- i.e. it reports a *perfect* translation generator precisely
where the method should fail hardest. Measured across grid x seed x batch,
``span_distance`` separated only 8/18 configurations while ``residual_l2``
separated 18/18 with a worst-case ratio of 1772x. See
``docs/design/V0_33_NONPERIODIC_GENERATORS_AND_MASK_PRESERVING_BRIDGE.md``.
"""

from __future__ import annotations

import itertools
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
from pdelie.symmetry.methods.polynomial_translation_svd import PolynomialTranslationSvdMethod
from tests._helpers.admissibility_dose_response import (
    DOSE_RESPONSE_ATOL,
    DOSE_RESPONSE_FIXTURE_PATH,
    DOSE_RESPONSE_PDE_NAMES,
    DOSE_RESPONSE_RTOL,
    measure_dose_response,
)
from tests._helpers.admissibility_dose_response import (
    load_fixture as load_dose_response_fixture,
)

_NUM_POINTS = 64
_SEED = 0

#: The frozen crash-test profile: a slowly-varying, strictly-positive nu(x)
#: whose mean equals the constant reference, so the failure is attributable to
#: x-dependence rather than to a shifted average coefficient.
_PROFILE_AMPLITUDE = 0.5

#: Minimum residual_l2 ratio for the admissibility crash test. Measured worst
#: case across grid {32,64,128} x seed {0,1,7} x batch {1,2} is 1772x, so this
#: threshold carries ~177x of headroom.
_CRASH_TEST_MIN_RATIO = 10.0


def _x_grid(num_points: int = _NUM_POINTS) -> np.ndarray:
    return np.linspace(0.0, DEFAULT_DOMAIN_LENGTH, num_points, endpoint=False, dtype=float)


def _sinusoidal_profile(base: float, num_points: int = _NUM_POINTS) -> np.ndarray:
    x = _x_grid(num_points)
    return base * (1.0 + _PROFILE_AMPLITUDE * np.sin(2.0 * np.pi * x / DEFAULT_DOMAIN_LENGTH))


def _heat_profile_callable(x: np.ndarray) -> np.ndarray:
    return 0.1 * (1.0 + _PROFILE_AMPLITUDE * np.sin(2.0 * np.pi * x / DEFAULT_DOMAIN_LENGTH))


# (label, generator, kwargs, base coefficient, residual evaluator factory)
_PDE_CASES = [
    (
        "heat_1d",
        generate_heat_1d_field_batch,
        {"batch_size": 1, "num_times": 17, "num_points": _NUM_POINTS, "seed": _SEED},
        0.1,
        lambda: HeatResidualEvaluator(diffusivity=0.1),
    ),
    (
        "burgers_1d",
        generate_burgers_1d_field_batch,
        {"batch_size": 1, "num_times": 33, "num_points": _NUM_POINTS, "seed": _SEED},
        0.1,
        lambda: BurgersResidualEvaluator(diffusivity=0.1),
    ),
    (
        "advection_diffusion_1d",
        generate_advection_diffusion_1d_field_batch,
        {"batch_size": 1, "num_times": 65, "num_points": _NUM_POINTS, "seed": _SEED},
        0.05,
        lambda: AdvectionDiffusionResidualEvaluator(advection_speed=0.75, diffusivity=0.05),
    ),
]
_PDE_IDS = [case[0] for case in _PDE_CASES]


# --------------------------------------------------------------------------
# Gate 1 -- constant path byte-preserved
# --------------------------------------------------------------------------


@pytest.mark.parametrize(("label", "generator", "kwargs", "base", "evaluator"), _PDE_CASES, ids=_PDE_IDS)
def test_constant_path_is_byte_preserved(label, generator, kwargs, base, evaluator) -> None:
    """Adding the kwarg must not perturb the constant-coefficient path at all.

    Absolute numerical pinning of these same generators lives in the v0.33e
    golden-numbers fixture, which runs in the release gate; this test covers the
    kwarg plumbing itself.
    """
    without_kwarg = generator(**kwargs)
    with_explicit_none = generator(**kwargs, diffusivity_profile=None)

    assert np.array_equal(without_kwarg.values, with_explicit_none.values)
    for axis in ("time", "x"):
        assert np.array_equal(without_kwarg.coords[axis], with_explicit_none.coords[axis])


def test_advection_diffusion_constant_path_byte_preserved_with_both_kwargs() -> None:
    kwargs = {"batch_size": 1, "num_times": 65, "num_points": _NUM_POINTS, "seed": _SEED}
    baseline = generate_advection_diffusion_1d_field_batch(**kwargs)
    explicit = generate_advection_diffusion_1d_field_batch(
        **kwargs, diffusivity_profile=None, advection_profile=None
    )
    assert np.array_equal(baseline.values, explicit.values)


@pytest.mark.parametrize(("label", "generator", "kwargs", "base", "evaluator"), _PDE_CASES, ids=_PDE_IDS)
def test_constant_path_records_constant_provenance(label, generator, kwargs, base, evaluator) -> None:
    """The uniform read path is populated even when no profile was supplied."""
    tags = generator(**kwargs).metadata["parameter_tags"]
    assert tags["nu_profile_kind"] == "constant"
    assert tags["nu_min"] == pytest.approx(base)
    assert tags["nu_max"] == pytest.approx(base)
    assert tags["nu_l2_norm"] == pytest.approx(base * np.sqrt(_NUM_POINTS))
    assert "nu_profile_hash" not in tags
    assert "nu_profile_callable_repr" not in tags


# --------------------------------------------------------------------------
# Gate 2 -- array and callable paths
# --------------------------------------------------------------------------


@pytest.mark.parametrize(("label", "generator", "kwargs", "base", "evaluator"), _PDE_CASES, ids=_PDE_IDS)
def test_array_profile_is_well_formed_with_provenance(label, generator, kwargs, base, evaluator) -> None:
    profile = _sinusoidal_profile(base)
    field = generator(**kwargs, diffusivity_profile=profile)
    field.validate()

    assert np.all(np.isfinite(field.values))
    assert field.values.shape == generator(**kwargs).values.shape

    tags = field.metadata["parameter_tags"]
    assert tags["nu_profile_kind"] == "array"
    assert tags["nu_profile_shape"] == [_NUM_POINTS]
    assert len(tags["nu_profile_hash"]) == 64
    assert tags["nu_min"] == pytest.approx(float(profile.min()))
    assert tags["nu_max"] == pytest.approx(float(profile.max()))
    assert tags["nu_l2_norm"] == pytest.approx(float(np.linalg.norm(profile)))


def test_callable_profile_records_source_and_matches_array_path() -> None:
    """The callable is sampled once on the grid; both paths must agree exactly."""
    array_field = generate_heat_1d_field_batch(
        batch_size=1, num_times=17, num_points=_NUM_POINTS, seed=_SEED,
        diffusivity_profile=_sinusoidal_profile(0.1),
    )
    callable_field = generate_heat_1d_field_batch(
        batch_size=1, num_times=17, num_points=_NUM_POINTS, seed=_SEED,
        diffusivity_profile=_heat_profile_callable,
    )
    assert np.array_equal(array_field.values, callable_field.values)

    tags = callable_field.metadata["parameter_tags"]
    assert tags["nu_profile_kind"] == "callable"
    # Source text, not repr: repr embeds a memory address and is not reproducible.
    assert "_heat_profile_callable" in tags["nu_profile_callable_repr"]
    assert "0x" not in tags["nu_profile_callable_repr"]
    assert "nu_profile_hash" not in tags


def test_array_profile_hash_is_deterministic_and_value_sensitive() -> None:
    kwargs = {"batch_size": 1, "num_times": 17, "num_points": _NUM_POINTS, "seed": _SEED}
    profile = _sinusoidal_profile(0.1)
    first = generate_heat_1d_field_batch(**kwargs, diffusivity_profile=profile)
    second = generate_heat_1d_field_batch(**kwargs, diffusivity_profile=profile.copy())
    assert (
        first.metadata["parameter_tags"]["nu_profile_hash"]
        == second.metadata["parameter_tags"]["nu_profile_hash"]
    )

    perturbed = profile.copy()
    perturbed[0] *= 1.0001
    third = generate_heat_1d_field_batch(**kwargs, diffusivity_profile=perturbed)
    assert (
        third.metadata["parameter_tags"]["nu_profile_hash"]
        != first.metadata["parameter_tags"]["nu_profile_hash"]
    )


def test_advection_profile_is_supported_and_may_be_signed() -> None:
    """Advection speed is signed, so the positivity check must not apply to it."""
    kwargs = {"batch_size": 1, "num_times": 65, "num_points": _NUM_POINTS, "seed": _SEED}
    profile = -0.75 * (1.0 + _PROFILE_AMPLITUDE * np.sin(2.0 * np.pi * _x_grid() / DEFAULT_DOMAIN_LENGTH))
    field = generate_advection_diffusion_1d_field_batch(**kwargs, advection_profile=profile)
    field.validate()

    tags = field.metadata["parameter_tags"]
    assert tags["c_profile_kind"] == "array"
    assert tags["c_max"] < 0.0
    assert np.all(np.isfinite(field.values))
    # The untouched coefficient still reports as constant.
    assert tags["nu_profile_kind"] == "constant"


def test_advection_diffusion_accepts_both_profiles_simultaneously() -> None:
    kwargs = {"batch_size": 1, "num_times": 65, "num_points": _NUM_POINTS, "seed": _SEED}
    field = generate_advection_diffusion_1d_field_batch(
        **kwargs,
        diffusivity_profile=_sinusoidal_profile(0.05),
        advection_profile=_sinusoidal_profile(0.75),
    )
    field.validate()
    assert np.all(np.isfinite(field.values))
    assert field.metadata["parameter_tags"]["nu_profile_kind"] == "array"
    assert field.metadata["parameter_tags"]["c_profile_kind"] == "array"


# --------------------------------------------------------------------------
# Gate 3 -- typed errors before any numerical work
# --------------------------------------------------------------------------


@pytest.mark.parametrize(("label", "generator", "kwargs", "base", "evaluator"), _PDE_CASES, ids=_PDE_IDS)
def test_shape_mismatch_raises_shape_validation_error(label, generator, kwargs, base, evaluator) -> None:
    with pytest.raises(ShapeValidationError, match="one value per spatial grid point"):
        generator(**kwargs, diffusivity_profile=np.full(_NUM_POINTS + 3, base))


@pytest.mark.parametrize(
    ("bad_profile", "match"),
    [
        (np.full(_NUM_POINTS, np.nan), "finite"),
        (np.full(_NUM_POINTS, np.inf), "finite"),
        (np.full(_NUM_POINTS, -0.1), "strictly positive"),
        (np.zeros(_NUM_POINTS), "strictly positive"),
    ],
    ids=["nan", "inf", "negative", "zero"],
)
def test_invalid_diffusivity_values_raise_scope_validation_error(bad_profile, match) -> None:
    with pytest.raises(ScopeValidationError, match=match):
        generate_heat_1d_field_batch(
            batch_size=1, num_times=17, num_points=_NUM_POINTS, seed=_SEED,
            diffusivity_profile=bad_profile,
        )


def test_callable_with_wrong_arity_raises_scope_validation_error() -> None:
    with pytest.raises(ScopeValidationError, match="single positional argument"):
        generate_heat_1d_field_batch(
            batch_size=1, num_times=17, num_points=_NUM_POINTS, seed=_SEED,
            diffusivity_profile=lambda a, b: a,
        )


def test_callable_returning_wrong_shape_raises_shape_validation_error() -> None:
    with pytest.raises(ShapeValidationError, match="one value per spatial grid point"):
        generate_heat_1d_field_batch(
            batch_size=1, num_times=17, num_points=_NUM_POINTS, seed=_SEED,
            diffusivity_profile=lambda x: np.ones(x.size + 1),
        )


def test_validation_precedes_numerical_work() -> None:
    """A malformed profile must fail without the generator integrating anything.

    Guarded by supplying a grid large enough that a completed rollout would be
    conspicuous, and asserting the typed error still surfaces immediately.
    """
    with pytest.raises(ScopeValidationError):
        generate_burgers_1d_field_batch(
            batch_size=4, num_times=257, num_points=256, seed=_SEED,
            diffusivity_profile=np.full(256, -1.0),
        )


# --------------------------------------------------------------------------
# Gate 4 -- the admissibility crash test
# --------------------------------------------------------------------------


@pytest.mark.parametrize(("label", "generator", "kwargs", "base", "evaluator"), _PDE_CASES, ids=_PDE_IDS)
def test_admissibility_crash_test_residual_l2(label, generator, kwargs, base, evaluator) -> None:
    """Constant-coefficient machinery run on variable-coefficient data must fail.

    The failure IS the diagnostic: applying a translation candidate without first
    checking for x-dependent coefficients is worse than not augmenting at all.
    """
    method = PolynomialTranslationSvdMethod()
    constant_field = generator(**kwargs)
    variable_field = generator(**kwargs, diffusivity_profile=_sinusoidal_profile(base))

    constant_result = method.fit(constant_field, residual_evaluator=evaluator())
    variable_result = method.fit(variable_field, residual_evaluator=evaluator())

    constant_l2 = constant_result.method_scores["residual_l2"]
    variable_l2 = variable_result.method_scores["residual_l2"]

    assert constant_l2 is not None and variable_l2 is not None
    assert variable_l2 >= _CRASH_TEST_MIN_RATIO * constant_l2, (
        f"{label}: variable-coefficient residual_l2 {variable_l2!r} did not exceed "
        f"{_CRASH_TEST_MIN_RATIO}x the constant-coefficient reference {constant_l2!r} "
        f"(ratio {variable_l2 / constant_l2:.1f}x). The admissibility crash test is "
        "empirical evidence, not analogy -- a shrinking ratio means the diagnostic is "
        "weakening."
    )


def test_crash_test_does_not_raise_it_reports() -> None:
    """The constant-coefficient method must run to completion on bad data.

    A raised exception would be a different (and weaker) claim than a completed
    fit carrying a measurably degraded score.
    """
    method = PolynomialTranslationSvdMethod()
    field = generate_heat_1d_field_batch(
        batch_size=1, num_times=17, num_points=_NUM_POINTS, seed=_SEED,
        diffusivity_profile=_sinusoidal_profile(0.1),
    )
    result = method.fit(field, residual_evaluator=HeatResidualEvaluator(diffusivity=0.1))

    assert set(result.method_scores) == {
        "span_distance",
        "residual_l2",
        "error_curve_max",
        "svd_condition_number",
    }
    assert result.method_scores["residual_l2"] is not None


# --------------------------------------------------------------------------
# Equation form and coefficient treatment policy
# --------------------------------------------------------------------------


@pytest.mark.parametrize(("label", "generator", "kwargs", "base", "evaluator"), _PDE_CASES, ids=_PDE_IDS)
def test_equation_form_and_treatment_policy_are_recorded(
    label, generator, kwargs, base, evaluator
) -> None:
    """v0.34a dispatches the residual evaluator on these tags rather than guessing."""
    tags = generator(**kwargs).metadata["parameter_tags"]
    assert tags["nu_form"] == "conservative_divergence"
    assert tags["nu_treatment_policy"] == "fixed_background"


def test_advection_form_is_recorded_on_advection_diffusion() -> None:
    tags = generate_advection_diffusion_1d_field_batch(
        batch_size=1, num_times=65, num_points=_NUM_POINTS, seed=_SEED
    ).metadata["parameter_tags"]
    assert tags["c_form"] == "nonconservative_c_ux"


@pytest.mark.parametrize(("label", "generator", "kwargs", "base", "evaluator"), _PDE_CASES, ids=_PDE_IDS)
def test_diffusivity_forms_differ_for_variable_nu(label, generator, kwargs, base, evaluator) -> None:
    """The two forms are genuinely different operators, not a recorded-only label."""
    profile = _sinusoidal_profile(base)
    conservative = generator(**kwargs, diffusivity_profile=profile)
    nonconservative = generator(
        **kwargs, diffusivity_profile=profile, diffusivity_form="nonconservative_nu_uxx"
    )
    assert not np.allclose(conservative.values, nonconservative.values)
    assert nonconservative.metadata["parameter_tags"]["nu_form"] == "nonconservative_nu_uxx"


def test_advection_forms_differ_for_variable_c() -> None:
    kwargs = {"batch_size": 1, "num_times": 65, "num_points": _NUM_POINTS, "seed": _SEED}
    profile = _sinusoidal_profile(0.75)
    nonconservative = generate_advection_diffusion_1d_field_batch(**kwargs, advection_profile=profile)
    conservative = generate_advection_diffusion_1d_field_batch(
        **kwargs, advection_profile=profile, advection_form="conservative_divergence"
    )
    assert not np.allclose(nonconservative.values, conservative.values)
    assert conservative.metadata["parameter_tags"]["c_form"] == "conservative_divergence"


@pytest.mark.parametrize(("label", "generator", "kwargs", "base", "evaluator"), _PDE_CASES, ids=_PDE_IDS)
def test_form_selection_does_not_disturb_the_constant_path(
    label, generator, kwargs, base, evaluator
) -> None:
    """The forms coincide for constant nu, so the byte-preserved path must not move."""
    baseline = generator(**kwargs)
    other_form = generator(**kwargs, diffusivity_form="nonconservative_nu_uxx")
    assert np.array_equal(baseline.values, other_form.values)


@pytest.mark.parametrize(
    ("kwarg", "value"),
    [("diffusivity_form", "bogus"), ("diffusivity_form", None), ("diffusivity_form", 1)],
)
def test_unknown_equation_form_raises_scope_validation_error(kwarg, value) -> None:
    with pytest.raises(ScopeValidationError, match="diffusivity_form must be one of"):
        generate_heat_1d_field_batch(
            batch_size=1, num_times=17, num_points=_NUM_POINTS, seed=_SEED, **{kwarg: value}
        )


def test_unknown_advection_form_raises_scope_validation_error() -> None:
    with pytest.raises(ScopeValidationError, match="advection_form must be one of"):
        generate_advection_diffusion_1d_field_batch(
            batch_size=1, num_times=65, num_points=_NUM_POINTS, seed=_SEED, advection_form="bogus"
        )


# --------------------------------------------------------------------------
# Dose-response: the crash test's underlying scientific claim
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def pinned_dose_response() -> dict:
    return {entry["name"]: entry for entry in load_dose_response_fixture()["pdes"]}


@pytest.fixture(scope="module")
def measured_dose_response() -> dict:
    """Measured once per module -- the full sweep is the expensive part of this file."""
    return {entry["name"]: entry for entry in measure_dose_response()}


@pytest.mark.parametrize("pde_name", DOSE_RESPONSE_PDE_NAMES)
def test_dose_response_matches_pinned_fixture(
    pde_name: str, pinned_dose_response: dict, measured_dose_response: dict
) -> None:
    """The measured curve must reproduce the pinned one within cross-BLAS tolerance."""
    fixture = pinned_dose_response
    measured = measured_dose_response

    expected_points = fixture[pde_name]["dose_response"]
    observed_points = measured[pde_name]["dose_response"]
    assert [point["alpha"] for point in observed_points] == [
        point["alpha"] for point in expected_points
    ]

    for expected, observed in zip(expected_points, observed_points, strict=True):
        tolerance = DOSE_RESPONSE_ATOL + DOSE_RESPONSE_RTOL * abs(expected["residual_l2"])
        assert abs(observed["residual_l2"] - expected["residual_l2"]) <= tolerance, (
            f"{pde_name} dose-response drifted at alpha={expected['alpha']}: "
            f"expected {expected['residual_l2']!r}, observed {observed['residual_l2']!r}."
        )


@pytest.mark.parametrize("pde_name", DOSE_RESPONSE_PDE_NAMES)
def test_dose_response_is_strictly_monotonic_in_alpha(pde_name: str, pinned_dose_response: dict) -> None:
    """Stronger x-dependence must degrade the constant-coefficient fit further."""
    entry = pinned_dose_response[pde_name]
    ratios = [point["ratio_to_constant_reference"] for point in entry["dose_response"]]
    assert all(
        later > earlier for earlier, later in itertools.pairwise(ratios)
    ), f"{pde_name} dose-response is not strictly increasing: {ratios}"


@pytest.mark.parametrize("pde_name", DOSE_RESPONSE_PDE_NAMES)
def test_alpha_zero_control_isolates_the_integrator(pde_name: str, pinned_dose_response: dict) -> None:
    """alpha=0 routes a constant array through the RK4 variable path.

    Its ratio must sit at ~1.0: the variable-coefficient scheme reproduces the
    closed-form constant-coefficient result when nu is constant. This is what
    makes the growth at alpha > 0 attributable to x-dependence rather than to
    having switched numerical schemes.
    """
    entry = pinned_dose_response[pde_name]
    control = entry["dose_response"][0]
    assert control["alpha"] == 0.0
    assert control["ratio_to_constant_reference"] == pytest.approx(1.0, rel=1e-6)


@pytest.mark.parametrize("pde_name", DOSE_RESPONSE_PDE_NAMES)
def test_frozen_crash_test_amplitude_clears_the_gate_in_the_fixture(pde_name: str, pinned_dose_response: dict) -> None:
    """The pinned curve must agree with the binary gate at the frozen alpha=0.5."""
    entry = pinned_dose_response[pde_name]
    at_frozen_alpha = next(
        point for point in entry["dose_response"] if point["alpha"] == _PROFILE_AMPLITUDE
    )
    assert at_frozen_alpha["ratio_to_constant_reference"] >= _CRASH_TEST_MIN_RATIO


def test_dose_response_fixture_is_strict_json() -> None:
    payload = json.loads(DOSE_RESPONSE_FIXTURE_PATH.read_text(encoding="utf-8"))
    json.dumps(payload, allow_nan=False)
    assert payload["summary_type"] == "pdelie_admissibility_dose_response_fixture"
    assert payload["diffusivity_form"] == "conservative_divergence"
    assert payload["last_regeneration_reason"].strip()


def test_span_distance_is_not_a_usable_crash_gate() -> None:
    """Pin the reason gate 4 asserts residual_l2 instead of span_distance.

    This configuration drives ``reference_fallback_used`` True, which collapses
    ``span_distance`` to exactly 0.0 -- better than the constant-coefficient
    reference, i.e. inverted. If a future selection-policy change makes
    span_distance usable here, this test fails and the gate can be revisited.
    """
    method = PolynomialTranslationSvdMethod()
    field = generate_heat_1d_field_batch(
        batch_size=2, num_times=17, num_points=_NUM_POINTS, seed=_SEED,
        diffusivity_profile=_sinusoidal_profile(0.1),
    )
    result = method.fit(field, residual_evaluator=HeatResidualEvaluator(diffusivity=0.1))

    assert result.fit_diagnostics["reference_fallback_used"] is True
    assert result.method_scores["span_distance"] == 0.0
