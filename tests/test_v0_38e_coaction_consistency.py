"""v0.38e: CR-1 .. CR-8, and the parameter-target repair in the executor.

Rules frozen in ``docs/design/v0_38e_hypothesis_freeze.md``.
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
from pdelie.actions.coaction_consistency import (
    COACTION_CONSISTENCY_SCHEMA_KEYS,
    COACTION_CONSISTENCY_SUMMARY_TYPE,
    COACTION_DIAGNOSES,
    COACTION_STATUSES,
    LEGAL_STATUS_DIAGNOSIS_PAIRS,
    PARAMETER_TARGET_KEY,
    declared_parameter_targets,
    summarize_coaction_consistency,
)
from pdelie.actions.execute import execute_bundle
from pdelie.actions.execution_config import ActionExecutionConfig
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


def _bundle(
    parameters: dict[str, object],
    *,
    parameter_action: ActionRef | None,
) -> ProblemActionBundle:
    return ProblemActionBundle(
        problem_instance=_problem(parameters),
        state_action=ActionRef("state", "identity", "id0"),
        domain_action=ActionRef("domain", "identity", "id0"),
        boundary_action=ActionRef("domain", "identity", "id0"),
        coefficient_field_actions={},
        parameter_action=parameter_action,
        expected_residual_relation=ExpectedResidualRelation(
            equation_relation="equivalence_transformation",
            parameter_relation="transformed" if parameter_action else "preserved",
            coefficient_relation="not_applicable",
            domain_relation="preserved",
            boundary_relation="preserved",
            expected_operator=ExpectedResidualOperator("identity"),
        ),
    )


def _rescale(factor: float = 3.0, targets: list[str] | None = None) -> ActionRef:
    parameters: dict[str, object] = {"factor": factor}
    if targets is not None:
        parameters[PARAMETER_TARGET_KEY] = targets
    return ActionRef("parameter", "scalar_rescale", "r", parameters)


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


# --------------------------------------------------------------------------
# CR-1, CR-2, CR-7 -- schema shape
# --------------------------------------------------------------------------


def test_cr1_payload_has_exactly_sixteen_keys_in_the_frozen_order() -> None:
    assert len(COACTION_CONSISTENCY_SCHEMA_KEYS) == 16
    payload = summarize_coaction_consistency(_bundle({"nu": 0.1}, parameter_action=None))
    assert tuple(payload) == COACTION_CONSISTENCY_SCHEMA_KEYS
    assert len(payload) == 16


def test_cr2_it_is_a_new_summary_type_on_a_new_payload() -> None:
    """New value, new payload, new function -- nothing existing is reshaped.

    The 22-key ``discovery_task_result`` schema is guarded in its own three
    files; restating it here would be a copy that can drift from the original.
    What is checked here is the half those files cannot see: that this
    ``summary_type`` is genuinely new rather than a second producer of an
    existing one.
    """
    import re
    from pathlib import Path

    payload = summarize_coaction_consistency(_bundle({"nu": 0.1}, parameter_action=None))
    assert payload["summary_type"] == COACTION_CONSISTENCY_SUMMARY_TYPE
    assert payload["summary_schema_version"] == "0.1"
    assert payload["summary_type"] != "discovery_task_result"

    src = Path(__file__).resolve().parents[1] / "src" / "pdelie"
    producers = [
        path.name
        for path in src.rglob("*.py")
        if re.search(
            rf'"summary_type"\s*:\s*"{re.escape(COACTION_CONSISTENCY_SUMMARY_TYPE)}"'
            rf'|=\s*"{re.escape(COACTION_CONSISTENCY_SUMMARY_TYPE)}"',
            path.read_text(),
        )
    ]
    assert producers == ["coaction_consistency.py"], (
        f"{COACTION_CONSISTENCY_SUMMARY_TYPE!r} is emitted from {producers}; a "
        f"summary_type must have exactly one producer"
    )


def test_cr7_payload_is_strict_json() -> None:
    payload = summarize_coaction_consistency(
        _bundle({"nu": 0.1}, parameter_action=_rescale())
    )
    json.dumps(payload, allow_nan=False)


def test_cr5_scientific_payload_is_hashed_and_metadata_is_not() -> None:
    """Rerunning elsewhere must not change the hash of what was observed."""
    bundle = _bundle({"nu": 0.1}, parameter_action=_rescale())
    first = summarize_coaction_consistency(
        bundle, execution_metadata={"host": "a", "elapsed_s": 1.0}
    )
    second = summarize_coaction_consistency(
        bundle, execution_metadata={"host": "b", "elapsed_s": 99.0}
    )
    assert first["scientific_payload_hash"] == second["scientific_payload_hash"]
    assert first["execution_metadata"] != second["execution_metadata"]


def test_cr5_a_scientific_change_does_change_the_hash() -> None:
    """Otherwise the hash would be insensitive to everything, not just metadata."""
    unnamed = summarize_coaction_consistency(
        _bundle({"nu": 0.1, "c": 2.0}, parameter_action=_rescale())
    )
    named = summarize_coaction_consistency(
        _bundle({"nu": 0.1, "c": 2.0}, parameter_action=_rescale(targets=["nu"]))
    )
    assert unnamed["scientific_payload_hash"] != named["scientific_payload_hash"]


# --------------------------------------------------------------------------
# CR-3, CR-4 -- every legal pair reachable, illegal pairs refused
# --------------------------------------------------------------------------


def test_cr4_the_legal_pair_table_is_a_strict_subset() -> None:
    every = {(s, d) for s in COACTION_STATUSES for d in COACTION_DIAGNOSES}
    assert LEGAL_STATUS_DIAGNOSIS_PAIRS < every, (
        "if every pair were legal the table would constrain nothing"
    )
    assert len(LEGAL_STATUS_DIAGNOSIS_PAIRS) == 5


def test_cr3_not_applicable_is_reachable() -> None:
    payload = summarize_coaction_consistency(_bundle({"nu": 0.1}, parameter_action=None))
    assert payload["consistency_status"] == "not_applicable"
    assert payload["diagnosis"] == "declaration_and_execution_agree"
    assert payload["parameter_target_declaration"] == "not_applicable"


def test_cr3_consistent_via_an_explicit_target_is_reachable() -> None:
    payload = summarize_coaction_consistency(
        _bundle({"nu": 0.1, "c": 2.0}, parameter_action=_rescale(targets=["nu"]))
    )
    assert payload["consistency_status"] == "consistent"
    assert payload["parameter_target_declaration"] == "explicit"
    assert payload["parameter_targets_resolved"] == ["nu"]


def test_cr3_consistent_by_exhaustion_is_reachable_and_labelled_differently() -> None:
    """One candidate: unambiguous, but the target was still not named.

    ``absent`` and ``explicit`` are kept distinct so the v0.37c cases -- which
    are all in this state -- are not retroactively described as having named
    something they did not.
    """
    payload = summarize_coaction_consistency(
        _bundle({"nu": 0.1}, parameter_action=_rescale())
    )
    assert payload["consistency_status"] == "consistent"
    assert payload["parameter_target_declaration"] == "absent"
    assert payload["parameter_targets_resolved"] == ["nu"]
    assert "only numeric parameter" in payload["diagnosis_detail"]


def test_cr3_indeterminate_target_ambiguous_is_reachable() -> None:
    """The §1 finding, as a report rather than a silent mis-execution."""
    payload = summarize_coaction_consistency(
        _bundle({"nu_baseline": 0.1, "advection_speed": 2.0}, parameter_action=_rescale())
    )
    assert payload["consistency_status"] == "indeterminate"
    assert payload["diagnosis"] == "target_ambiguous"
    assert payload["parameter_target_candidates"] == ["advection_speed", "nu_baseline"]
    assert payload["parameter_targets_resolved"] is None


def test_cr3_inconsistent_declared_not_executed_is_reachable() -> None:
    payload = summarize_coaction_consistency(
        _bundle({"label": "x"}, parameter_action=_rescale())
    )
    assert payload["consistency_status"] == "inconsistent"
    assert payload["diagnosis"] == "declared_not_executed"


def test_cr3_every_legal_pair_the_summariser_can_emit_is_covered() -> None:
    """Guard the coverage claim itself, rather than trusting the list above."""
    emitted = set()
    for parameters, action in (
        ({"nu": 0.1}, None),
        ({"nu": 0.1, "c": 2.0}, _rescale(targets=["nu"])),
        ({"nu": 0.1}, _rescale()),
        ({"nu_baseline": 0.1, "advection_speed": 2.0}, _rescale()),
        ({"label": "x"}, _rescale()),
    ):
        payload = summarize_coaction_consistency(_bundle(parameters, parameter_action=action))
        emitted.add((payload["consistency_status"], payload["diagnosis"]))

    unreachable = LEGAL_STATUS_DIAGNOSIS_PAIRS - emitted
    assert unreachable <= {("inconsistent", "executed_not_declared")}, (
        f"legal pairs with no constructed case: {sorted(unreachable)}"
    )
    assert emitted <= LEGAL_STATUS_DIAGNOSIS_PAIRS, (
        f"emitted a pair the table calls illegal: {sorted(emitted - LEGAL_STATUS_DIAGNOSIS_PAIRS)}"
    )


# --------------------------------------------------------------------------
# CR-6 -- absence is a sentinel, never a number-shaped None
# --------------------------------------------------------------------------


def test_cr6_absence_is_explicit_and_never_nan() -> None:
    payload = summarize_coaction_consistency(
        _bundle({"nu_baseline": 0.1, "advection_speed": 2.0}, parameter_action=_rescale())
    )
    assert payload["parameter_targets_resolved"] is None
    serialized = json.dumps(payload, allow_nan=False)
    assert "NaN" not in serialized and "Infinity" not in serialized


# --------------------------------------------------------------------------
# target declaration -- refusals
# --------------------------------------------------------------------------


def test_a_bare_string_target_is_refused_rather_than_iterated() -> None:
    bundle = _bundle(
        {"nu": 0.1},
        parameter_action=ActionRef(
            "parameter", "scalar_rescale", "r", {"factor": 2.0, PARAMETER_TARGET_KEY: "nu"}
        ),
    )
    with pytest.raises(ScopeValidationError, match="iterate as characters"):
        declared_parameter_targets(bundle)


def test_an_empty_target_list_is_refused() -> None:
    bundle = _bundle({"nu": 0.1}, parameter_action=_rescale(targets=[]))
    with pytest.raises(ScopeValidationError, match="targeting nothing"):
        declared_parameter_targets(bundle)


def test_a_target_that_is_not_a_parameter_is_refused() -> None:
    bundle = _bundle({"nu": 0.1}, parameter_action=_rescale(targets=["viscosity"]))
    with pytest.raises(ScopeValidationError, match="not parameters of this problem"):
        declared_parameter_targets(bundle)


def test_booleans_are_not_rescale_candidates() -> None:
    """``bool`` subclasses ``int``; a flag scaled by 2.0 is not a quantity."""
    payload = summarize_coaction_consistency(
        _bundle({"nu": 0.1, "use_flux_form": True}, parameter_action=_rescale())
    )
    assert payload["parameter_target_candidates"] == ["nu"]
    assert payload["consistency_status"] == "consistent"


# --------------------------------------------------------------------------
# The executor repair
# --------------------------------------------------------------------------


def test_the_executor_refuses_an_ambiguous_target_rather_than_rescaling_all() -> None:
    """The measured defect, now a refusal.

    Before v0.38e this rescaled ``advection_speed`` from 2.0 to 6.0 under an
    action that named only a factor.
    """
    bundle = _bundle(
        {"nu_baseline": 0.1, "advection_speed": 2.0}, parameter_action=_rescale()
    )
    with pytest.raises(ScopeValidationError, match="not decidable from the bundle"):
        execute_bundle(bundle, _field(), _config())


def test_an_explicit_target_rescales_only_what_it_names() -> None:
    bundle = _bundle(
        {"nu_baseline": 0.1, "advection_speed": 2.0},
        parameter_action=_rescale(factor=3.0, targets=["nu_baseline"]),
    )
    result = execute_bundle(bundle, _field(), _config())
    assert result.transformed_parameters["nu_baseline"] == pytest.approx(0.3)
    assert result.transformed_parameters["advection_speed"] == pytest.approx(2.0), (
        "a parameter the action does not name must be left alone"
    )


def test_a_single_parameter_problem_is_unchanged_by_the_repair() -> None:
    """The v0.37c population. This is why the change alters no released result."""
    bundle = _bundle({"nu_baseline": 0.1}, parameter_action=_rescale(factor=2.0))
    result = execute_bundle(bundle, _field(), _config())
    assert result.transformed_parameters == {"nu_baseline": pytest.approx(0.2)}


def test_every_shipped_benchmark_case_still_has_one_numeric_parameter() -> None:
    """The premise the previous test rests on, asserted rather than assumed.

    This is the reason the v0.37c suite could not observe the defect: on a
    one-parameter problem, "rescale all" and "rescale the declared one" are the
    same set. If a future case adds a second numeric parameter without naming a
    target, the executor now refuses -- and this test names why before the
    benchmark run does.
    """
    import ast
    from pathlib import Path

    from pdelie.benchmarks.parameter_equivariant import BENCHMARK_CASES

    assert BENCHMARK_CASES, "no cases to check"

    # The spec is built inside the runner, so the parameter mapping is read from
    # the source rather than by executing a benchmark sweep here.
    source = (
        Path(__file__).resolve().parents[1]
        / "src/pdelie/benchmarks/parameter_equivariant.py"
    ).read_text()
    tree = ast.parse(source)
    parameter_mappings = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.keyword)
        and node.arg == "parameters"
        and isinstance(node.value, ast.Dict)
    ]
    assert parameter_mappings, "no parameters= mapping found in the benchmark runner"

    spec_mappings = [
        node
        for node in parameter_mappings
        if any(
            isinstance(key, ast.Constant) and key.value == "nu_baseline"
            for key in node.value.keys  # type: ignore[attr-defined]
        )
    ]
    assert spec_mappings, "no ProblemInstanceSpec parameters mapping carrying nu_baseline"
    for mapping in spec_mappings:
        keys = [
            key.value
            for key in mapping.value.keys  # type: ignore[attr-defined]
            if isinstance(key, ast.Constant)
        ]
        assert keys == ["nu_baseline"], (
            f"a benchmark case now declares parameters {keys}. With more than one "
            f"numeric parameter an unnamed rescale target is ambiguous and the "
            f"executor refuses it -- declare "
            f"{PARAMETER_TARGET_KEY!r} on the parameter action."
        )
