"""v0.37b: executing an action bundle, and classifying what was executed.

The six runtime paths must each be reachable and must each be distinguishable,
because a report that cannot say which combination it measured is a report
nobody can act on.

The exactness discipline is the other thing under test here. ``exact_grid_shift``
permutes samples and adds no error of its own, so a residual difference is
attributable to the transformation. A shift that is not a whole number of cells
is refused rather than rounded -- rounding would measure a different action than
the one declared, and the resulting error would describe the rounding.
"""

from __future__ import annotations

import numpy as np
import pytest

from pdelie.actions import (
    RUNTIME_PATHS,
    ActionExecutionConfig,
    ActionRef,
    CoefficientFieldRef,
    CoordinateFieldAction,
    ExpectedResidualOperator,
    ExpectedResidualRelation,
    ProblemActionBundle,
    ProblemInstanceSpec,
    classify_runtime_path,
    execute_bundle,
    execute_state_action,
    shift_cells,
    validate_action_bundle,
)
from pdelie.data import generate_heat_1d_field_batch
from pdelie.errors import ScopeValidationError
from pdelie.residuals import HeatResidualEvaluator

NUM_POINTS = 32


@pytest.fixture(scope="module")
def field():
    return generate_heat_1d_field_batch(
        batch_size=1, num_times=32, num_points=NUM_POINTS, seed=7
    )


@pytest.fixture(scope="module")
def dx(field) -> float:
    return float(np.diff(np.asarray(field.coords["x"]))[0])


@pytest.fixture()
def config() -> ActionExecutionConfig:
    return ActionExecutionConfig(
        interpolation_backend="exact_grid_shift",
        numerical_tolerances={"rtol": 1e-9, "atol": 1e-12},
        seed=None,
        deterministic_expected=True,
    )


def _ref(treatment: str = "fixed_background") -> CoefficientFieldRef:
    kwargs = {}
    if treatment == "co_transformable_background":
        kwargs["analytical_spec"] = {"profile": "sinusoidal"}
    return CoefficientFieldRef(
        field_name="nu", coordinate_dependency=("x",), treatment=treatment, **kwargs
    )


def _problem(treatment: str = "fixed_background") -> ProblemInstanceSpec:
    return ProblemInstanceSpec(
        equation_family="heat_1d",
        equation_form="nonconservative",
        parameters={"nu_baseline": 0.1},
        coefficient_fields={"nu": _ref(treatment)},
        spatial_axis_name="x",
        time_axis_name="t",
        domain_type="periodic_uniform",
    )


def _action(target: str, family: str, **parameters) -> ActionRef:
    return ActionRef(
        action_target=target,
        action_family=family,
        action_parameter_id=f"{family}_{target}",
        parameters=parameters,
    )


def _relation(**kwargs) -> ExpectedResidualRelation:
    kwargs.setdefault("equation_relation", "same_equation")
    kwargs.setdefault("parameter_relation", "preserved")
    kwargs.setdefault("coefficient_relation", "fixed")
    kwargs.setdefault("domain_relation", "preserved")
    kwargs.setdefault("boundary_relation", "preserved")
    kwargs.setdefault("expected_operator", ExpectedResidualOperator(family="identity"))
    return ExpectedResidualRelation(**kwargs)


def _bundle(
    *,
    state: ActionRef | None = None,
    coefficient: CoordinateFieldAction | None = None,
    parameter: ActionRef | None = None,
    treatment: str = "fixed_background",
    relation: ExpectedResidualRelation | None = None,
) -> ProblemActionBundle:
    identity = _action("state", "identity")
    return ProblemActionBundle(
        problem_instance=_problem(treatment),
        state_action=state or identity,
        domain_action=_action("domain", "identity"),
        boundary_action=_action("domain", "identity"),
        coefficient_field_actions={"nu": coefficient or CoordinateFieldAction(family="identity")},
        expected_residual_relation=relation or _relation(),
        parameter_action=parameter,
    )


def _paths(dx: float) -> dict[str, ProblemActionBundle]:
    """One bundle per runtime path."""
    translate = _action("state", "spatial_translation", offset=3 * dx)
    shift = CoordinateFieldAction(family="shift", parameters={"offset": 3 * dx})
    opposed = CoordinateFieldAction(family="shift", parameters={"offset": -3 * dx})
    rescale = _action("parameter", "scalar_rescale", factor=2.0)
    co = "co_transformable_background"
    moved = _relation(coefficient_relation="co_transformed",
                      equation_relation="equivalence_transformation")
    return {
        "P-1": _bundle(state=translate),
        "P-2": _bundle(coefficient=shift, treatment=co, relation=moved),
        "P-3": _bundle(state=translate, coefficient=shift, treatment=co, relation=moved),
        "P-4": _bundle(state=translate, coefficient=opposed, treatment=co, relation=moved),
        "P-5": _bundle(parameter=rescale, relation=_relation(parameter_relation="transformed")),
        "P-6": _bundle(
            state=translate,
            coefficient=shift,
            parameter=rescale,
            treatment=co,
            relation=_relation(
                coefficient_relation="co_transformed",
                parameter_relation="transformed",
                equation_relation="equivalence_transformation",
            ),
        ),
    }


# --- the six paths ----------------------------------------------------------


@pytest.mark.parametrize("path", RUNTIME_PATHS)
def test_every_runtime_path_is_reachable(path: str, dx: float) -> None:
    assert classify_runtime_path(_paths(dx)[path]) == path


def test_the_six_paths_are_distinct(dx: float) -> None:
    observed = [classify_runtime_path(b) for b in _paths(dx).values()]
    assert sorted(observed) == sorted(RUNTIME_PATHS)
    assert len(set(observed)) == 6


def test_p4_differs_from_p3_only_by_the_sign_of_the_coefficient_shift(dx: float) -> None:
    """The deliberate obstruction is a direction, not a magnitude."""
    paths = _paths(dx)
    p3 = paths["P-3"].coefficient_field_actions["nu"].parameters["offset"]
    p4 = paths["P-4"].coefficient_field_actions["nu"].parameters["offset"]
    assert p3 == -p4
    assert classify_runtime_path(paths["P-3"]) == "P-3"
    assert classify_runtime_path(paths["P-4"]) == "P-4"


def test_every_path_bundle_is_a_legal_bundle(dx: float) -> None:
    for bundle in _paths(dx).values():
        validate_action_bundle(bundle)


def test_an_unclassifiable_bundle_is_refused(dx: float) -> None:
    """Refused, not reported as one of the six."""
    bundle = _bundle()  # identity everywhere, no parameter action
    with pytest.raises(ScopeValidationError, match="does not match any of the six"):
        classify_runtime_path(bundle)


# --- exactness --------------------------------------------------------------


def test_a_whole_cell_shift_converts_exactly() -> None:
    assert shift_cells(0.6, 0.2) == 3
    assert shift_cells(-0.6, 0.2) == -3
    assert shift_cells(0.0, 0.2) == 0


def test_a_fractional_shift_is_refused_not_rounded() -> None:
    """Rounding would measure a different action than the one declared."""
    with pytest.raises(ScopeValidationError, match="refused rather than rounded"):
        shift_cells(0.25, 0.2)


def test_a_fractional_state_shift_fails_at_execution(field, config, dx: float) -> None:
    bundle = _bundle(state=_action("state", "spatial_translation", offset=0.5 * dx))
    with pytest.raises(ScopeValidationError, match="whole number of cells"):
        execute_state_action(bundle, field, config)


def test_unimplemented_backends_raise_rather_than_silently_degrade(field, dx: float) -> None:
    config = ActionExecutionConfig(
        interpolation_backend="fourier",
        numerical_tolerances={"rtol": 1e-9},
        seed=None,
        deterministic_expected=True,
    )
    with pytest.raises(ScopeValidationError, match="not implemented at v0.37b"):
        execute_state_action(_bundle(state=_action("state", "spatial_translation", offset=dx)),
                             field, config)


def test_a_full_period_shift_is_the_identity(field, config, dx: float) -> None:
    """A periodic domain shifted by its whole width returns the same samples."""
    bundle = _bundle(state=_action("state", "spatial_translation", offset=NUM_POINTS * dx))
    out = execute_state_action(bundle, field, config)
    assert np.array_equal(np.asarray(out.values), np.asarray(field.values))


def test_the_state_shift_permutes_rather_than_resamples(field, config, dx: float) -> None:
    """Exactness means the multiset of samples is unchanged."""
    bundle = _bundle(state=_action("state", "spatial_translation", offset=5 * dx))
    out = execute_state_action(bundle, field, config)
    assert np.array_equal(
        np.sort(np.asarray(out.values).ravel()), np.sort(np.asarray(field.values).ravel())
    )


def test_identity_state_action_returns_the_field_unchanged(field, config) -> None:
    out = execute_state_action(_bundle(), field, config)
    assert np.array_equal(np.asarray(out.values), np.asarray(field.values))


# --- the physics the whole arc rests on -------------------------------------


def test_translation_is_a_symmetry_of_constant_coefficient_heat(field, config, dx: float) -> None:
    """R(Tu) == T R(u) for constant nu -- measured, not assumed.

    This is the P-1 baseline. If it did not hold at machine precision, every
    obstruction result downstream would be uninterpretable.
    """
    bundle = _bundle(state=_action("state", "spatial_translation", offset=3 * dx))
    result = execute_bundle(bundle, field, config)
    evaluator = HeatResidualEvaluator(diffusivity=0.1)
    original = evaluator.evaluate(field).residual
    transformed = evaluator.evaluate(result.transformed_field).residual
    rolled = np.roll(original, 3, axis=field.dims.index("x"))
    assert np.abs(transformed - rolled).max() < 1e-12


def test_execution_is_deterministic(field, config, dx: float) -> None:
    bundle = _bundle(state=_action("state", "spatial_translation", offset=3 * dx))
    first = execute_bundle(bundle, field, config)
    second = execute_bundle(bundle, field, config)
    assert np.array_equal(
        np.asarray(first.transformed_field.values), np.asarray(second.transformed_field.values)
    )
    assert first.as_dict() == second.as_dict()


# --- coefficient and parameter actions --------------------------------------


def test_coefficient_shift_moves_the_background_by_the_same_cells(field, config, dx: float) -> None:
    values = np.linspace(0.0, 1.0, NUM_POINTS)
    bundle = _bundle(
        coefficient=CoordinateFieldAction(family="shift", parameters={"offset": 4 * dx}),
        treatment="co_transformable_background",
        relation=_relation(coefficient_relation="co_transformed",
                           equation_relation="equivalence_transformation"),
    )
    result = execute_bundle(bundle, field, config, coefficient_values={"nu": values})
    assert result.coefficient_shift_cells["nu"] == 4
    assert np.array_equal(result.transformed_coefficients["nu"], np.roll(values, 4))


def test_scalar_rescale_scales_every_numeric_parameter(field, config) -> None:
    bundle = _bundle(
        parameter=_action("parameter", "scalar_rescale", factor=3.0),
        relation=_relation(parameter_relation="transformed"),
    )
    result = execute_bundle(bundle, field, config)
    assert result.transformed_parameters["nu_baseline"] == pytest.approx(0.3)


def test_a_missing_coefficient_array_is_refused_when_an_action_needs_it(
    field, config, dx: float
) -> None:
    bundle = _bundle(
        coefficient=CoordinateFieldAction(family="shift", parameters={"offset": dx}),
        treatment="co_transformable_background",
        relation=_relation(coefficient_relation="co_transformed",
                           equation_relation="equivalence_transformation"),
    )
    with pytest.raises(ScopeValidationError, match="nothing to transform"):
        execute_bundle(bundle, field, config, coefficient_values={})


def test_execute_bundle_requires_an_execution_config(field, dx: float) -> None:
    bundle = _bundle(state=_action("state", "spatial_translation", offset=dx))
    with pytest.raises(ScopeValidationError, match="ActionExecutionConfig"):
        execute_bundle(bundle, field, {"interpolation_backend": "exact_grid_shift"})  # type: ignore[arg-type]


# --- scope ------------------------------------------------------------------


def test_v0_37b_does_not_touch_the_residual_layer() -> None:
    """v0.34a's dispatch is stable; v0.37b composes with it and changes nothing."""
    import subprocess

    changed = subprocess.run(
        ["git", "diff", "--name-only", "v0.36.0", "--", "src/pdelie/residuals/"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.split()
    # The two hoists landed in v0.37a; nothing beyond them may change.
    assert all(
        name.endswith(("heat_1d.py", "burgers_1d.py")) for name in changed
    ), f"v0.37 changed residual modules beyond the two constant hoists: {changed}"
