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
    RESERVED_UNREACHABLE_PAIRS,
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


def test_cr3_every_reachable_legal_pair_has_a_constructed_case() -> None:
    """B-1 of the pilot freeze, as a standing test.

    Pilot run 1 blocked here: the legal table advertised a pair nothing could
    produce. The reserved set is excluded BY NAME, so a pair that quietly stops
    being producible fails this rather than being absorbed into the exception.
    """
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

    expected = LEGAL_STATUS_DIAGNOSIS_PAIRS - RESERVED_UNREACHABLE_PAIRS
    assert emitted == expected, (
        f"not produced: {sorted(expected - emitted)}; "
        f"produced but not legal: {sorted(emitted - LEGAL_STATUS_DIAGNOSIS_PAIRS)}"
    )


def test_reserved_pairs_are_genuinely_unreachable() -> None:
    """Prove the reservation by reading the branches, not by failing to hit one.

    A reserved pair is a claim that no code path emits it. Absence of a test
    that produces it is not evidence -- that is how the block in run 1 arose in
    the first place. This parses every literal (status, diagnosis) assignment in
    the summariser and asserts the reserved pairs are not among them.
    """
    import ast
    from pathlib import Path

    import pdelie.actions.coaction_consistency as module

    tree = ast.parse(Path(module.__file__).read_text())
    function = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == "summarize_coaction_consistency"
    )
    emitted_literals: set[tuple[str, str]] = set()
    for node in ast.walk(function):
        if not isinstance(node, ast.Assign):
            continue
        target = node.targets[0]
        if not (isinstance(target, ast.Tuple) and len(target.elts) == 2):
            continue
        names = [e.id for e in target.elts if isinstance(e, ast.Name)]
        if names != ["status", "diagnosis"]:
            continue
        if isinstance(node.value, ast.Tuple) and len(node.value.elts) == 2:
            values = [
                e.value for e in node.value.elts if isinstance(e, ast.Constant)
            ]
            if len(values) == 2:
                emitted_literals.add((values[0], values[1]))

    assert emitted_literals, "found no (status, diagnosis) assignments to inspect"
    assert emitted_literals <= LEGAL_STATUS_DIAGNOSIS_PAIRS, (
        f"the summariser can emit an illegal pair: "
        f"{sorted(emitted_literals - LEGAL_STATUS_DIAGNOSIS_PAIRS)}"
    )
    leaked = emitted_literals & RESERVED_UNREACHABLE_PAIRS
    assert not leaked, (
        f"{sorted(leaked)} is reserved as unreachable but the summariser now "
        f"emits it. Lift the reservation deliberately -- and give it a test "
        f"case -- rather than leaving the table describing the old behaviour."
    )
    assert emitted_literals == LEGAL_STATUS_DIAGNOSIS_PAIRS - RESERVED_UNREACHABLE_PAIRS


def test_the_reserved_set_is_a_strict_subset_of_the_legal_set() -> None:
    """A reservation must reserve something the table actually declares."""
    assert RESERVED_UNREACHABLE_PAIRS < LEGAL_STATUS_DIAGNOSIS_PAIRS
    assert RESERVED_UNREACHABLE_PAIRS, (
        "an empty reserved set means every legal pair is reachable; if that "
        "becomes true, delete this test rather than leaving it vacuous"
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


def test_every_multi_parameter_case_names_a_target_or_expects_a_block() -> None:
    """The invariant that replaces "every case has one parameter".

    That premise was true through v0.37c and is deliberately false from v0.38e:
    C-7 and C-8 are the first cases with two numeric parameters, which is the
    only population on which the unnamed-target ambiguity is observable at all.

    What must hold instead is the rule the executor enforces. A case with more
    than one numeric parameter either names its rescale target, or declares that
    it expects to be blocked. A case that does neither would raise mid-sweep and
    take the whole benchmark run down with it.
    """
    from pdelie.benchmarks.parameter_equivariant import BENCHMARK_CASES

    assert BENCHMARK_CASES, "no cases to check"
    multi = [
        case
        for case in BENCHMARK_CASES.values()
        if 1 + len(case.extra_numeric_parameters) > 1
    ]
    assert multi, (
        "no multi-parameter case exists; C-7/C-8 are what make the ambiguity "
        "observable, and without one of them this suite is back where v0.37c was"
    )

    for case in multi:
        action_parameters = dict(case.parameter_action_parameters or {})
        names_target = PARAMETER_TARGET_KEY in action_parameters
        expects_block = case.expected_classification == "blocked_ambiguous_parameter_target"
        assert names_target or expects_block or case.parameter_action_family is None, (
            f"case {case.case_id!r} declares "
            f"{1 + len(case.extra_numeric_parameters)} numeric parameters and a "
            f"{case.parameter_action_family!r} action with no "
            f"{PARAMETER_TARGET_KEY!r}, but does not expect to be blocked. The "
            f"executor refuses this, so the sweep would raise rather than record."
        )
        assert not (names_target and expects_block), (
            f"case {case.case_id!r} both names a target and expects a block; "
            f"naming one resolves the ambiguity, so it cannot also be blocked"
        )


def test_the_v0_37c_population_is_still_single_parameter() -> None:
    """Why v0.37c could not see the defect, kept as a standing statement."""
    from pdelie.benchmarks.parameter_equivariant import (
        BENCHMARK_CASES,
        V0_37C_CASE_IDS,
    )

    for case_id in V0_37C_CASE_IDS:
        case = BENCHMARK_CASES[case_id]
        assert not case.extra_numeric_parameters, (
            f"{case_id} gained a second numeric parameter. That is allowed, but "
            f"it changes what the signed v0.37c freeze measured, so the freeze "
            f"scope must be revisited rather than the case quietly extended."
        )
