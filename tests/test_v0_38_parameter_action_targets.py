"""v0.38: the eight release-blocking cases for parameter-action targeting.

The defect these exist for: a ``scalar_rescale`` declared with no target was
applied to *every* numeric parameter, so a rescale meant for the viscosity also
tripled the advection speed. A one-parameter benchmark cannot distinguish those
two implementations, which is why it survived a full release arc.

Case 8 -- an unrelated parameter is exactly unchanged -- is the decisive
negative control. The other seven can all pass while the executor quietly
touches something nobody named.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from pdelie.actions.action_bundle import (
    ExpectedResidualOperator,
    ExpectedResidualRelation,
    ProblemActionBundle,
)
from pdelie.actions.action_ref import ActionRef
from pdelie.actions.execute import execute_bundle
from pdelie.actions.execution_config import ActionExecutionConfig
from pdelie.actions.parameter_action_spec import (
    ParameterActionSpec,
    as_parameter_action_spec,
)
from pdelie.actions.problem_spec import ProblemInstanceSpec
from pdelie.contracts import FieldBatch
from pdelie.errors import ScopeValidationError


def _problem(parameters: dict[str, object]) -> ProblemInstanceSpec:
    return ProblemInstanceSpec(
        equation_family="advection_diffusion_1d",
        equation_form="nonconservative",
        parameters=parameters,
        coefficient_fields={},
        spatial_axis_name="x",
        time_axis_name="time",
        domain_type="periodic_uniform",
    )


def _bundle(parameters: dict[str, object], action: object | None) -> ProblemActionBundle:
    return ProblemActionBundle(
        problem_instance=_problem(parameters),
        state_action=ActionRef("state", "identity", "id0"),
        domain_action=ActionRef("domain", "identity", "id0"),
        boundary_action=ActionRef("domain", "identity", "id0"),
        coefficient_field_actions={},
        parameter_action=action,
        expected_residual_relation=ExpectedResidualRelation(
            equation_relation="equivalence_transformation",
            parameter_relation="transformed" if action else "preserved",
            coefficient_relation="not_applicable",
            domain_relation="preserved",
            boundary_relation="preserved",
            expected_operator=ExpectedResidualOperator("identity"),
        ),
    )


def _rescale(factor: float = 3.0, targets: object = None) -> ParameterActionSpec:
    return ParameterActionSpec(
        action_family="scalar_rescale",
        action_parameter_id="r",
        target_parameters=targets,
        parameters={"factor": factor},
    )


def _field() -> FieldBatch:
    x = np.linspace(0.0, 2.0 * np.pi, 8, endpoint=False)
    return FieldBatch(
        values=np.zeros((2, 4, 8, 1)),
        dims=("batch", "time", "x", "var"),
        coords={"time": np.linspace(0.0, 0.2, 4), "x": x},
        var_names=["u"],
        metadata={
            "boundary_conditions": {"x": "periodic"},
            "coordinate_system": "cartesian",
            "grid_regularity": "uniform",
            "grid_type": "rectilinear",
            "parameter_tags": {},
        },
        preprocess_log=[],
    )


def _config() -> ActionExecutionConfig:
    return ActionExecutionConfig(
        seed=None,
        interpolation_backend="exact_grid_shift",
        numerical_tolerances={"rtol": 1e-9, "atol": 1e-12},
        deterministic_expected=True,
    )


def _run(parameters: dict[str, object], action: object | None):
    return execute_bundle(_bundle(parameters, action), _field(), _config())


# --------------------------------------------------------------------------
# 1. One numeric parameter
# --------------------------------------------------------------------------


def test_1_one_numeric_parameter_is_unambiguous_by_exhaustion() -> None:
    """No target named, but only one candidate. Allowed, and recorded as such.

    This is the entire v0.37c population, so it must keep working -- the repair
    changes no released result.
    """
    result = _run({"nu_baseline": 0.1}, _rescale(factor=2.0))
    assert result.transformed_parameters == {"nu_baseline": pytest.approx(0.2)}
    assert result.declared_target_parameters is None
    assert result.parameter_targets_applied == ("nu_baseline",)
    assert result.parameters_untouched == ()


# --------------------------------------------------------------------------
# 2. Two numeric parameters, one targeted
# --------------------------------------------------------------------------


def test_2_two_parameters_one_targeted() -> None:
    result = _run(
        {"nu_baseline": 0.1, "advection_speed": 2.0},
        _rescale(factor=3.0, targets=["nu_baseline"]),
    )
    assert result.transformed_parameters["nu_baseline"] == pytest.approx(0.3)
    assert result.declared_target_parameters == ("nu_baseline",)
    assert result.parameter_targets_applied == ("nu_baseline",)
    assert result.parameters_untouched == ("advection_speed",)


# --------------------------------------------------------------------------
# 3. Two explicitly targeted parameters
# --------------------------------------------------------------------------


def test_3_two_explicitly_targeted_parameters() -> None:
    """Rescaling both is legal -- when it is *declared*, not assumed."""
    result = _run(
        {"nu_baseline": 0.1, "advection_speed": 2.0},
        _rescale(factor=3.0, targets=["nu_baseline", "advection_speed"]),
    )
    assert result.transformed_parameters["nu_baseline"] == pytest.approx(0.3)
    assert result.transformed_parameters["advection_speed"] == pytest.approx(6.0)
    assert result.declared_target_parameters == ("advection_speed", "nu_baseline")
    assert result.parameters_untouched == ()


def test_3b_the_declared_both_case_is_distinguishable_from_the_old_defect() -> None:
    """Same numbers as the defect produced -- different, checkable provenance.

    Pre-v0.38 an *undeclared* rescale produced exactly this arithmetic. The
    payload is what separates them: `declared_target_parameters` is populated
    here and would have been absent then.
    """
    declared = _run(
        {"nu_baseline": 0.1, "advection_speed": 2.0},
        _rescale(factor=3.0, targets=["nu_baseline", "advection_speed"]),
    )
    assert declared.declared_target_parameters is not None
    assert set(declared.declared_target_parameters) == set(
        declared.parameter_targets_applied
    )


# --------------------------------------------------------------------------
# 4. Missing target on a multi-parameter problem -> blocked
# --------------------------------------------------------------------------


def test_4_missing_target_on_a_multi_parameter_problem_is_blocked() -> None:
    with pytest.raises(ScopeValidationError, match="not decidable from the bundle"):
        _run({"nu_baseline": 0.1, "advection_speed": 2.0}, _rescale())


def test_4b_the_block_names_the_candidates() -> None:
    """A refusal a caller cannot act on is only half a refusal."""
    with pytest.raises(ScopeValidationError) as excinfo:
        _run({"nu_baseline": 0.1, "advection_speed": 2.0}, _rescale())
    message = str(excinfo.value)
    assert "advection_speed" in message and "nu_baseline" in message
    assert "target_parameters" in message


# --------------------------------------------------------------------------
# 5. Unknown target -> blocked
# --------------------------------------------------------------------------


def test_5_an_unknown_target_is_blocked_at_construction() -> None:
    with pytest.raises(ScopeValidationError, match="not parameters of this problem"):
        _bundle({"nu_baseline": 0.1}, _rescale(targets=["viscosity"]))


def test_5b_a_partially_unknown_target_set_is_blocked() -> None:
    """One valid name must not license the rest."""
    with pytest.raises(ScopeValidationError, match="not parameters of this problem"):
        _bundle(
            {"nu_baseline": 0.1, "advection_speed": 2.0},
            _rescale(targets=["nu_baseline", "viscosity"]),
        )


# --------------------------------------------------------------------------
# 6. Duplicate targets -> blocked
# --------------------------------------------------------------------------


def test_6_duplicate_targets_are_blocked() -> None:
    with pytest.raises(ScopeValidationError, match="repeats"):
        _rescale(targets=["nu_baseline", "nu_baseline"])


def test_6b_an_empty_target_set_is_blocked_and_is_not_none() -> None:
    """`()` and `None` are different statements and must not collapse."""
    with pytest.raises(ScopeValidationError, match="targeting nothing"):
        _rescale(targets=[])
    assert _rescale(targets=None).target_parameters is None


def test_6c_a_bare_string_is_blocked_rather_than_iterated() -> None:
    with pytest.raises(ScopeValidationError, match="iterate as characters"):
        _rescale(targets="nu_baseline")


# --------------------------------------------------------------------------
# 7. Target set in the bundle hash, and round-trip serialisation
# --------------------------------------------------------------------------


def test_7_the_target_set_changes_the_bundle_hash() -> None:
    """Two bundles differing only in target must not be the same bundle."""
    parameters = {"nu_baseline": 0.1, "advection_speed": 2.0}
    one = _bundle(parameters, _rescale(targets=["nu_baseline"]))
    both = _bundle(parameters, _rescale(targets=["nu_baseline", "advection_speed"]))
    assert one.identity() != both.identity()


def test_7b_an_undeclared_target_hashes_differently_from_a_declared_one() -> None:
    """Otherwise C-7 and C-8 would be the same bundle."""
    single = {"nu_baseline": 0.1}
    undeclared = _bundle(single, _rescale())
    declared = _bundle(single, _rescale(targets=["nu_baseline"]))
    assert undeclared.identity() != declared.identity(), (
        "a bundle that names its target and one that does not are different "
        "declarations even when they execute identically"
    )


def test_7c_target_order_does_not_change_the_hash() -> None:
    """A set of targets is a set; hashing must not depend on typing order."""
    parameters = {"nu_baseline": 0.1, "advection_speed": 2.0}
    forward = _bundle(parameters, _rescale(targets=["advection_speed", "nu_baseline"]))
    reverse = _bundle(parameters, _rescale(targets=["nu_baseline", "advection_speed"]))
    assert forward.identity() == reverse.identity()


def test_7d_the_spec_round_trips_through_strict_json() -> None:
    for targets in (None, ["nu_baseline"], ["nu_baseline", "advection_speed"]):
        spec = _rescale(factor=2.5, targets=targets)
        payload = spec.as_dict()
        json.dumps(payload, allow_nan=False)
        restored = ParameterActionSpec.from_dict(payload)
        assert restored == spec
        assert restored.identity() == spec.identity()


def test_7e_an_action_ref_upgrades_losslessly() -> None:
    """v0.38e call sites keep working, and produce the same stored value."""
    legacy = ActionRef(
        "parameter",
        "scalar_rescale",
        "r",
        {"factor": 3.0, "target_parameters": ["nu_baseline"]},
    )
    upgraded = as_parameter_action_spec(legacy)
    assert upgraded.target_parameters == ("nu_baseline",)
    assert upgraded.parameters == {"factor": 3.0}, (
        "the target key must not remain in the free-form mapping as well; two "
        "copies is how they come to disagree"
    )
    assert upgraded == _rescale(factor=3.0, targets=["nu_baseline"])


def test_7f_a_constructed_bundle_stores_only_the_typed_form() -> None:
    bundle = _bundle(
        {"nu_baseline": 0.1},
        ActionRef("parameter", "scalar_rescale", "r", {"factor": 2.0}),
    )
    assert isinstance(bundle.parameter_action, ParameterActionSpec)


# --------------------------------------------------------------------------
# 8. An unrelated parameter is exactly unchanged -- the decisive control
# --------------------------------------------------------------------------


def test_8_an_unrelated_parameter_is_exactly_unchanged() -> None:
    """Exactly. Not approximately: it must not be arithmetic'd at all.

    This is the assertion the original defect would have failed. Every other
    test here can pass while the executor quietly multiplies a parameter nobody
    named -- `2.0 * 1.0` looks identical to "left alone" under approx.
    """
    original = 2.0
    result = _run(
        {"nu_baseline": 0.1, "advection_speed": original},
        _rescale(factor=3.0, targets=["nu_baseline"]),
    )
    observed = result.transformed_parameters["advection_speed"]
    assert observed == original, f"advection_speed moved: {original} -> {observed}"
    assert observed.hex() == original.hex(), (
        "advection_speed is numerically equal but not bit-identical, so it was "
        "put through an arithmetic operation it was never a target of"
    )
    assert "advection_speed" in result.parameters_untouched
    assert "advection_speed" not in result.parameter_targets_applied


def test_8b_untouched_is_the_exact_complement_of_applied() -> None:
    """The two lists must partition the candidates, with nothing missing."""
    parameters = {"nu_baseline": 0.1, "advection_speed": 2.0, "amplitude": 5.0}
    result = _run(parameters, _rescale(factor=3.0, targets=["nu_baseline"]))
    assert set(result.parameter_targets_applied) | set(result.parameters_untouched) == set(
        parameters
    )
    assert not set(result.parameter_targets_applied) & set(result.parameters_untouched)


def test_8c_the_execution_payload_reports_all_three_lists() -> None:
    result = _run(
        {"nu_baseline": 0.1, "advection_speed": 2.0},
        _rescale(factor=3.0, targets=["nu_baseline"]),
    )
    payload = result.as_dict()
    assert payload["declared_target_parameters"] == ["nu_baseline"]
    assert payload["parameter_targets_applied"] == ["nu_baseline"]
    assert payload["parameters_untouched"] == ["advection_speed"]
    json.dumps(payload, allow_nan=False)
