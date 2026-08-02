"""v0.38e: CB-1 .. CB-4, and the derived-equation-form repair.

Rules frozen in ``docs/design/v0_38e_hypothesis_freeze.md``.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from pdelie.benchmarks.parameter_equivariant import (
    BENCHMARK_CASES,
    PROFILE_REGISTRY,
    V0_37C_CASE_IDS,
    V0_38E_CASE_IDS,
    _build_field,
    _derive_equation_form,
    build_coefficient_field,
    run_admissibility_benchmark,
)
from pdelie.errors import ScopeValidationError


def _numeric_parameter_count(case_id: str) -> int:
    case = BENCHMARK_CASES[case_id]
    return 1 + len(case.extra_numeric_parameters)  # nu_baseline plus extras


# --------------------------------------------------------------------------
# Freeze scoping
# --------------------------------------------------------------------------


def test_every_case_belongs_to_exactly_one_freeze() -> None:
    """A signed freeze covers the population it measured, and no other.

    Without this, a case added later silently falls under a freeze that never
    measured it -- or under none, which is worse because nothing says so.
    """
    assigned = list(V0_37C_CASE_IDS) + list(V0_38E_CASE_IDS)
    assert len(assigned) == len(set(assigned)), "a case is assigned to two freezes"
    assert set(assigned) == set(BENCHMARK_CASES), (
        f"unassigned cases: {sorted(set(BENCHMARK_CASES) - set(assigned))}; "
        f"every case must name the freeze that governs it"
    )


# --------------------------------------------------------------------------
# CB-1 -- the pair is the first multi-parameter population
# --------------------------------------------------------------------------


def test_cb1_the_pair_declares_two_numeric_parameters_each() -> None:
    for case_id in V0_38E_CASE_IDS:
        assert _numeric_parameter_count(case_id) >= 2, (
            f"{case_id} declares {_numeric_parameter_count(case_id)} numeric "
            f"parameter(s); the ambiguity it exercises needs at least two"
        )


def test_cb1_the_v0_37c_cases_remain_single_parameter() -> None:
    """The reason v0.37c could not observe the defect, still true and stated."""
    for case_id in V0_37C_CASE_IDS:
        assert _numeric_parameter_count(case_id) == 1


def test_cb1_the_pair_differs_in_exactly_one_declaration() -> None:
    """C-7 and C-8 must be attributable: one difference, or the pair proves nothing."""
    seven = BENCHMARK_CASES["C-7"].as_dict()
    eight = BENCHMARK_CASES["C-8"].as_dict()
    differing = {
        key
        for key in seven
        if seven[key] != eight[key]
    }
    assert differing == {
        "case_id",
        "parameter_action_parameters",
        "expected_classification",
        "is_deliberate_obstruction",
    }, (
        f"C-7 and C-8 differ in {sorted(differing)}. They must differ only in "
        f"whether the target is named (plus the labels that follow from it), or "
        f"a difference in outcome is not attributable to the declaration."
    )
    assert "target_parameters" in dict(seven["parameter_action_parameters"])
    assert "target_parameters" not in dict(eight["parameter_action_parameters"])
    assert (
        dict(seven["parameter_action_parameters"])["factor"]
        == dict(eight["parameter_action_parameters"])["factor"]
    ), "the factor must match, or the pair varies two things at once"


# --------------------------------------------------------------------------
# CB-2, CB-3 -- the confirming case measures; the obstruction is refused
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def pilot_run() -> dict:
    return run_admissibility_benchmark(phase="pilot", seeds=[13])


def _rows(run: dict, case_id: str) -> list[dict]:
    return [r for r in run["measurements"] if r["case_id"] == case_id]


def test_cb2_c7_measures_and_leaves_its_second_parameter_alone(pilot_run: dict) -> None:
    rows = _rows(pilot_run, "C-7")
    assert rows, "C-7 produced no measurements"
    for row in rows:
        assert row["outcome"] == "measured"
        assert row["coaction_consistency_status"] == "consistent"
        assert row["coaction_diagnosis"] == "declaration_and_execution_agree"
        assert row["absolute_error_l2"] is not None


def test_cb2_c7_rescales_only_the_named_parameter() -> None:
    """Measured through the executor, not asserted from the declaration."""
    from pdelie.benchmarks.parameter_equivariant import _measure_case

    result = _measure_case(
        BENCHMARK_CASES["C-7"], alpha=0.4, seed=13, num_times=32, num_points=32
    )
    assert result["outcome"] == "measured"
    assert result["coaction_consistency_status"] == "consistent"

    baseline = BENCHMARK_CASES["C-7"]
    factor = dict(baseline.parameter_action_parameters or {})["factor"]
    declared_speed = float(baseline.extra_numeric_parameters["advection_speed"])
    transformed = result["transformed_parameters"]

    assert transformed["nu_baseline"] == pytest.approx(
        PROFILE_REGISTRY[baseline.profile_id].baseline * factor
    ), "the named target was not rescaled"
    assert transformed["advection_speed"] == pytest.approx(declared_speed), (
        f"advection_speed is {transformed['advection_speed']}, expected "
        f"{declared_speed} unchanged. Before v0.38e the rescale hit every "
        f"numeric parameter and this is the assertion that would have caught it."
    )


def test_cb3_c8_is_blocked_with_the_pre_registered_diagnosis(pilot_run: dict) -> None:
    """B-2 of the freeze: anything else here blocks the confirmatory freeze."""
    rows = _rows(pilot_run, "C-8")
    assert rows, "C-8 produced no measurements"
    for row in rows:
        assert row["outcome"] == "blocked_ambiguous_parameter_target"
        assert row["coaction_consistency_status"] == "indeterminate"
        assert row["coaction_diagnosis"] == "target_ambiguous"


def test_cb3_a_blocked_row_carries_none_never_nan_or_zero(pilot_run: dict) -> None:
    """Zero would read as a perfect measurement; NaN would not survive JSON."""
    for row in _rows(pilot_run, "C-8"):
        for key in ("absolute_error_l2", "absolute_error_linf", "comparison_scale"):
            assert row[key] is None, f"{key} is {row[key]!r}; a blocked case has no number"


def test_cb3_blocked_and_measured_rows_share_a_key_set(pilot_run: dict) -> None:
    """So a consumer cannot skip blocked rows by KeyError and call it coverage."""
    measured = _rows(pilot_run, "C-7")[0]
    blocked = _rows(pilot_run, "C-8")[0]
    assert set(measured) == set(blocked)


# --------------------------------------------------------------------------
# CB-4 -- the pair is distinguishable
# --------------------------------------------------------------------------


def test_cb4_the_pair_never_reports_the_same_outcome(pilot_run: dict) -> None:
    seven = {r["outcome"] for r in _rows(pilot_run, "C-7")}
    eight = {r["outcome"] for r in _rows(pilot_run, "C-8")}
    assert seven.isdisjoint(eight), (
        f"C-7 and C-8 both report {sorted(seven & eight)}; the pair must be "
        f"distinguishable or it measures nothing"
    )


def test_cb4_c7_sits_clear_of_the_spectral_floor(pilot_run: dict) -> None:
    """A confirming case at the floor would be indistinguishable from a control."""
    control = [
        r["absolute_error_l2"]
        for r in _rows(pilot_run, "C-1")
        if r["absolute_error_l2"] is not None
    ]
    seven = [
        r["absolute_error_l2"]
        for r in _rows(pilot_run, "C-7")
        if r["absolute_error_l2"] is not None
    ]
    assert min(seven) > 1e6 * max(control), (
        f"C-7 min {min(seven):.3e} is not clear of the C-1 floor {max(control):.3e}"
    )


# --------------------------------------------------------------------------
# The derived-equation-form repair
# --------------------------------------------------------------------------


def test_the_equation_form_is_derived_and_names_the_operator_that_runs() -> None:
    """v0.38e: this was the literal "nonconservative" on every case.

    The evaluator dispatches on the field's ``nu_form`` provenance tag and took
    the conservative branch for every variable-coefficient case, so the declared
    form named an operator that produced none of the numbers.
    """
    field = _build_field("heat_1d", seed=13, num_times=16, num_points=16)
    x = np.asarray(field.coords["x"], dtype=float)
    coefficient = build_coefficient_field("sinusoidal", 0.5, x)

    assert field.metadata["parameter_tags"]["nu_form"] == "conservative_divergence"
    assert _derive_equation_form(field, coefficient) == "conservative"


def _form_difference_ratio(profile_id: str, alpha: float) -> float:
    """||nu' u_x|| / ||u_t - nu u_xx||, the exact gap between the two forms.

    ``d/dx(nu u_x) - nu u_xx == nu' u_x`` identically, so this is an ANALYTIC
    difference. An earlier version of this helper differenced a spectral
    ``u_xx`` against ``np.gradient(nu * u_x)``, which measures the gap between
    two discretizations and not the gap between the two forms -- it reported
    1.9e+03 on a constant coefficient, where the true difference is exactly
    zero. Same class as the v0.37c section-6 error, and caught the same way:
    by deriving the term instead of subtracting two numbers.
    """
    from pdelie.residuals.heat_1d import compute_derivatives

    field = _build_field("heat_1d", seed=13, num_times=32, num_points=32)
    x = np.asarray(field.coords["x"], dtype=float)
    nu = build_coefficient_field(profile_id, alpha, x)
    derivatives = compute_derivatives(field, backend="auto")
    u_t = derivatives.derivatives["u_t"]
    u_x = derivatives.derivatives["u_x"]
    u_xx = derivatives.derivatives["u_xx"]

    nu_prime = np.gradient(nu, float(np.diff(x)[0]))
    difference = nu_prime * u_x
    nonconservative = u_t - nu * u_xx
    return float(
        np.sqrt(np.sum(difference**2)) / np.sqrt(np.sum(nonconservative**2))
    )


def test_the_two_operators_really_do_differ_on_a_variable_coefficient() -> None:
    """Otherwise the correction above would be a relabelling of nothing."""
    ratio = _form_difference_ratio("sinusoidal", 0.5)
    assert ratio > 0.5, (
        f"the form difference is only {ratio:.3f} of the residual here, so this "
        f"profile cannot demonstrate that the form label matters"
    )


def test_the_forms_coincide_for_a_constant_coefficient() -> None:
    """The documented caveat, asserted rather than left as an assumption."""
    ratio = _form_difference_ratio("constant", 0.5)
    assert ratio == 0.0, (
        f"the forms differ by {ratio:.2e} on a constant coefficient. nu' is "
        f"identically zero there, so the difference term nu' u_x must be exactly "
        f"zero -- anything else means the coefficient is not actually constant."
    )


def test_an_unmapped_coefficient_form_is_refused_not_guessed() -> None:
    class FakeField:
        metadata = {"parameter_tags": {"nu_form": "some_new_form", "nu": 0.1}}

    with pytest.raises((ScopeValidationError, Exception)):
        _derive_equation_form(FakeField(), np.ones(8))


# --------------------------------------------------------------------------
# Run-level invariants
# --------------------------------------------------------------------------


def test_the_run_payload_is_strict_json(pilot_run: dict) -> None:
    json.dumps(pilot_run, allow_nan=False)


def test_the_run_covers_every_case(pilot_run: dict) -> None:
    covered = {r["case_id"] for r in pilot_run["measurements"]}
    assert covered == set(BENCHMARK_CASES)
