"""v0.37b: the residual commutation report.

Three properties are load-bearing and each has dedicated tests.

**The fit never overrides the analytical decision.** Two adversarial cases
construct residuals a least-squares fit explains almost perfectly but which the
declared relation says are violated. The verdict must stay ``violated`` in both.
The failure this guards against is the sentence *"the fit told us it was a
symmetry"*.

**Expected, observed and outcome are three fields.** A deliberate obstruction
that fails is a success for the benchmark and a failure for the transformation,
and one status word cannot say both.

**Only the science claims determinism.** The report contains a wall-clock
duration, so whole-dictionary byte equality is impossible. The scientific
payload is hashed and reproduces exactly; the execution metadata is checked for
schema stability only. A determinism test that passed on the whole dictionary
would only be passing because it had quietly excluded the timing.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from pdelie.actions import (
    BENCHMARK_OUTCOMES,
    COMMUTATION_REPORT_SUMMARY_TYPE,
    EXPECTED_CASES,
    OBSERVED_RELATION_STATUSES,
    ActionExecutionConfig,
    ActionRef,
    CoefficientFieldRef,
    CoordinateFieldAction,
    ExpectedResidualOperator,
    ExpectedResidualRelation,
    ProblemActionBundle,
    ProblemInstanceSpec,
    build_residual_commutation_report,
    execute_bundle,
    fit_diagnostic_operator,
)
from pdelie.data import generate_heat_1d_field_batch
from pdelie.errors import ShapeValidationError
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


def _bundle(dx: float, *, operator: ExpectedResidualOperator | None = None, opposed: bool = False):
    treatment = "co_transformable_background" if opposed else "fixed_background"
    kwargs = {"analytical_spec": {"profile": "sinusoidal"}} if opposed else {}
    ref = CoefficientFieldRef(
        field_name="nu", coordinate_dependency=("x",), treatment=treatment, **kwargs
    )
    problem = ProblemInstanceSpec(
        equation_family="heat_1d",
        equation_form="nonconservative",
        parameters={"nu_baseline": 0.1},
        coefficient_fields={"nu": ref},
        spatial_axis_name="x",
        time_axis_name="t",
        domain_type="periodic_uniform",
    )
    relation = ExpectedResidualRelation(
        equation_relation="equivalence_transformation" if opposed else "same_equation",
        parameter_relation="preserved",
        coefficient_relation="co_transformed" if opposed else "fixed",
        domain_relation="preserved",
        boundary_relation="preserved",
        expected_operator=operator or ExpectedResidualOperator(family="identity"),
    )
    return ProblemActionBundle(
        problem_instance=problem,
        state_action=ActionRef(
            action_target="state",
            action_family="spatial_translation",
            action_parameter_id="shift",
            parameters={"offset": 3 * dx},
        ),
        domain_action=ActionRef(
            action_target="domain", action_family="identity", action_parameter_id="id"
        ),
        boundary_action=ActionRef(
            action_target="domain", action_family="identity", action_parameter_id="id"
        ),
        coefficient_field_actions={
            "nu": CoordinateFieldAction(family="shift", parameters={"offset": -3 * dx})
            if opposed
            else CoordinateFieldAction(family="identity")
        },
        expected_residual_relation=relation,
    )


def _report(field, config, dx, *, bundle=None, original=None, transformed=None, runtime=0.01):
    bundle = bundle or _bundle(dx)
    execution = execute_bundle(
        bundle,
        field,
        config,
        coefficient_values={"nu": np.linspace(0.05, 0.15, NUM_POINTS)},
    )
    evaluator = HeatResidualEvaluator(diffusivity=0.1)
    base = evaluator.evaluate(field).residual
    if original is None:
        original = np.roll(base, 3, axis=field.dims.index("x"))
    if transformed is None:
        transformed = evaluator.evaluate(execution.transformed_field).residual
    return build_residual_commutation_report(
        bundle, execution, config, original, transformed, runtime_seconds=runtime
    )


# --- shape ------------------------------------------------------------------


def test_the_report_is_strict_json(field, config, dx) -> None:
    report = _report(field, config, dx)
    assert json.loads(json.dumps(report, allow_nan=False)) == report


def test_the_report_uses_summary_schema_version(field, config, dx) -> None:
    """The measured convention for payloads carrying summary_type: 34 vs 5."""
    report = _report(field, config, dx)
    assert report["summary_type"] == COMMUTATION_REPORT_SUMMARY_TYPE
    assert "summary_schema_version" in report
    assert "schema_version" not in report


def test_optional_evidence_is_nested_with_no_availability_booleans(field, config, dx) -> None:
    """C-5. Absence is a key being absent, not a paired boolean."""
    report = _report(field, config, dx)
    payload = report["scientific_payload"]
    assert "optional_evidence" in payload
    assert isinstance(payload["optional_evidence"], dict)
    flat = json.dumps(report)
    for forbidden in (
        "parameter_deltas_available",
        "coefficient_field_deltas_available",
        "expected_multiplier_available",
        "fitted_operator_diagnostic_available",
    ):
        assert forbidden not in flat


def test_the_payload_and_the_metadata_are_separate(field, config, dx) -> None:
    """C-6. Runtime cannot live inside something claiming byte determinism."""
    report = _report(field, config, dx)
    assert "runtime_seconds" in report["execution_metadata"]
    assert "runtime_seconds" not in json.dumps(report["scientific_payload"])


# --- determinism, honestly scoped -------------------------------------------


def test_the_scientific_payload_is_deterministic_across_runtimes(field, config, dx) -> None:
    fast = _report(field, config, dx, runtime=0.001)
    slow = _report(field, config, dx, runtime=12.5)
    assert fast["scientific_payload"] == slow["scientific_payload"]
    assert fast["scientific_result_hash"] == slow["scientific_result_hash"]


def test_whole_report_equality_is_deliberately_not_asserted(field, config, dx) -> None:
    """The reports differ, and that is correct rather than a defect.

    Asserting whole-dictionary equality could only pass by excluding the timing
    the report claims to carry -- which is the contradiction C-6 names.
    """
    fast = _report(field, config, dx, runtime=0.001)
    slow = _report(field, config, dx, runtime=12.5)
    assert fast != slow
    assert fast["execution_metadata"] != slow["execution_metadata"]


def test_execution_metadata_schema_is_stable(field, config, dx) -> None:
    fast = _report(field, config, dx, runtime=0.001)
    slow = _report(field, config, dx, runtime=12.5)
    assert set(fast["execution_metadata"]) == set(slow["execution_metadata"])


def test_the_hash_covers_the_science_and_nothing_else(field, config, dx) -> None:
    from pdelie.artifact import semantic_hash

    report = _report(field, config, dx)
    assert report["scientific_result_hash"] == semantic_hash(report["scientific_payload"])


# --- the three status fields ------------------------------------------------


def test_a_true_symmetry_is_confirmed(field, config, dx) -> None:
    payload = _report(field, config, dx)["scientific_payload"]
    assert payload["expected_case"] == "valid_relation"
    assert payload["observed_relation_status"] == "confirmed"
    assert payload["benchmark_outcome"] == "expected_result_observed"


def test_the_deliberate_obstruction_reads_without_contradiction(field, config, dx) -> None:
    """P-4: the transformation failed, and that is what the benchmark wanted."""
    bundle = _bundle(dx, opposed=True)
    evaluator = HeatResidualEvaluator(diffusivity=0.1)
    base = evaluator.evaluate(field).residual
    payload = _report(
        field,
        config,
        dx,
        bundle=bundle,
        original=np.roll(base, 3, axis=field.dims.index("x")),
        transformed=base * 1.5,
    )["scientific_payload"]
    assert payload["runtime_path"] == "P-4"
    assert payload["expected_case"] == "deliberate_obstruction"
    assert payload["observed_relation_status"] == "violated"
    assert payload["benchmark_outcome"] == "expected_result_observed"


def test_an_obstruction_that_unexpectedly_holds_is_flagged(field, config, dx) -> None:
    bundle = _bundle(dx, opposed=True)
    evaluator = HeatResidualEvaluator(diffusivity=0.1)
    base = np.roll(
        evaluator.evaluate(field).residual, 3, axis=field.dims.index("x")
    )
    payload = _report(
        field, config, dx, bundle=bundle, original=base, transformed=base
    )["scientific_payload"]
    assert payload["expected_case"] == "deliberate_obstruction"
    assert payload["observed_relation_status"] == "confirmed"
    assert payload["benchmark_outcome"] == "unexpected_result_observed"


def test_diagnostic_fitted_reports_no_relation_declared(field, config, dx) -> None:
    """R-A13, end to end."""
    bundle = _bundle(dx, operator=ExpectedResidualOperator(family="diagnostic_fitted"))
    payload = _report(field, config, dx, bundle=bundle)["scientific_payload"]
    assert payload["observed_relation_status"] == "no_relation_declared"
    assert payload["expected_case"] == "diagnostic_unknown"
    assert payload["benchmark_outcome"] == "not_evaluated"


@pytest.mark.parametrize("field_name,vocabulary", [
    ("expected_case", EXPECTED_CASES),
    ("observed_relation_status", OBSERVED_RELATION_STATUSES),
    ("benchmark_outcome", BENCHMARK_OUTCOMES),
])
def test_status_fields_draw_from_their_closed_vocabularies(
    field, config, dx, field_name: str, vocabulary
) -> None:
    payload = _report(field, config, dx)["scientific_payload"]
    assert payload[field_name] in vocabulary


# --- the fit never overrides the analytical decision ------------------------


def test_adversarial_one_a_near_perfect_fit_does_not_rescue_a_violation(
    field, config, dx
) -> None:
    """R' = 2R fits R' ~ cR perfectly, but the declared relation is identity."""
    evaluator = HeatResidualEvaluator(diffusivity=0.1)
    base = np.roll(evaluator.evaluate(field).residual, 3, axis=field.dims.index("x"))

    fit = fit_diagnostic_operator(base, base * 2.0)
    assert fit.fitted_multiplier == pytest.approx(2.0)
    assert fit.fit_r_squared == pytest.approx(1.0)

    # Now declare identity and feed the same pair. The fit is excellent; the
    # declared relation is nonetheless violated.
    declared = _bundle(dx, operator=ExpectedResidualOperator(family="affine",
                                                             parameters={"multiplier": 1.0,
                                                                         "offset": 0.0}))
    payload = _report(
        field, config, dx, bundle=declared, original=base, transformed=base * 2.0
    )["scientific_payload"]
    assert payload["observed_relation_status"] == "violated"
    evidence = payload["optional_evidence"]["fitted_operator_diagnostic"]
    assert evidence["fit_r_squared"] == pytest.approx(1.0)
    assert evidence["advisory_only"] is True


def test_adversarial_two_the_fit_is_attached_but_carries_no_verdict(
    field, config, dx
) -> None:
    """A perfect fit is reported as evidence and changes nothing."""
    bundle = _bundle(dx, operator=ExpectedResidualOperator(
        family="affine", parameters={"multiplier": 1.0, "offset": 0.0}))
    evaluator = HeatResidualEvaluator(diffusivity=0.1)
    base = np.roll(evaluator.evaluate(field).residual, 3, axis=field.dims.index("x"))
    payload = _report(
        field, config, dx, bundle=bundle, original=base, transformed=base * 7.0
    )["scientific_payload"]

    assert payload["observed_relation_status"] == "violated"
    evidence = payload["optional_evidence"]["fitted_operator_diagnostic"]
    assert evidence["fitted_multiplier"] == pytest.approx(7.0)
    # The diagnostic must not carry anything a reader could mistake for a verdict.
    for forbidden in ("status", "holds", "confirmed", "passed", "verdict"):
        assert forbidden not in evidence


def test_the_diagnostic_type_exposes_no_verdict_field() -> None:
    import dataclasses

    from pdelie.actions import FittedOperatorDiagnostic

    names = {f.name for f in dataclasses.fields(FittedOperatorDiagnostic)}
    assert not names & {"status", "holds", "verdict", "passed", "is_symmetry"}


def test_a_degenerate_fit_returns_none_not_zero() -> None:
    """A fit that could not run and a fit that returned zero are different facts."""
    zeros = np.zeros(16)
    fit = fit_diagnostic_operator(zeros, np.ones(16))
    assert fit.fitted_multiplier is None
    assert fit.degenerate_reason == "original_residual_is_identically_zero"


def test_no_fit_is_attached_for_families_that_declare_a_closed_form(
    field, config, dx
) -> None:
    """identity and scalar_multiplier are checkable without fitting anything."""
    payload = _report(field, config, dx)["scientific_payload"]
    assert "fitted_operator_diagnostic" not in payload["optional_evidence"]


# --- guards -----------------------------------------------------------------


def test_mismatched_residual_shapes_are_refused(field, config, dx) -> None:
    with pytest.raises(ShapeValidationError, match="not defined"):
        _report(field, config, dx, original=np.zeros((2, 2)), transformed=np.zeros((3, 3)))


def test_a_fit_between_mismatched_shapes_is_refused() -> None:
    with pytest.raises(ShapeValidationError, match="not meaningful"):
        fit_diagnostic_operator(np.zeros(4), np.zeros(5))
