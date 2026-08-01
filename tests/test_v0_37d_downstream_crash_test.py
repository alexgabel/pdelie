"""v0.37d: seven branches, and the two things that must not move.

**Blocking is measured, not asserted.** The four invalid branches must return
before discovery runs. That is checked by handing the bridge a task that
*raises on call* and asserting it never fires. Reading the code and seeing an
early return is not the same claim, and does not survive a refactor.

**The 22-key schema does not move.** ``discovery_task_result`` has had a 22-key
top level since v0.30.1. B-1 returns the task's payload with those keys
untouched; B-2/B-3 emit a *different* summary type with exactly two more.
"""

from __future__ import annotations

import json

import pytest

from pdelie.actions import (
    ActionRef,
    CoefficientFieldRef,
    CoordinateFieldAction,
    ExpectedResidualOperator,
    ExpectedResidualRelation,
    ProblemActionBundle,
    ProblemInstanceSpec,
)
from pdelie.downstream import (
    AUGMENTED_TASK_SUMMARY_TYPE,
    BLOCK_STATUSES,
    BRANCHES,
    BUNDLE_RELATION_STATUSES,
    augmented_key_count,
    classify_branch,
    run_downstream_with_action_bundle,
)
from pdelie.errors import ScopeValidationError
from pdelie.tasks import discovery as discovery_module

DX = 0.19634954084936207


class TaskWasCalled(AssertionError):
    """Raised by the sentinel task. Its appearance is the failure."""


def exploding_task() -> dict:
    raise TaskWasCalled("the discovery task ran on a blocked branch")


def _fake_task_result() -> dict:
    """A payload with exactly the 22 frozen top-level keys."""
    return {key: None for key in discovery_module._TASK_RESULT_TOP_LEVEL_KEYS} | {
        "summary_type": "discovery_task_result",
        "summary_schema_version": "0.1",
        "task_name": "v0_37d",
    }


def _ref(treatment: str = "fixed_background") -> CoefficientFieldRef:
    kwargs = {}
    if treatment == "co_transformable_background":
        kwargs["analytical_spec"] = {"profile": "sinusoidal"}
    return CoefficientFieldRef(
        field_name="nu", coordinate_dependency=("x",), treatment=treatment, **kwargs
    )


def _action(target: str, family: str, **parameters) -> ActionRef:
    return ActionRef(
        action_target=target,
        action_family=family,
        action_parameter_id=f"{family}_{target}",
        parameters=parameters,
    )


def _bundle(
    *,
    treatment: str = "fixed_background",
    coefficient_relation: str = "fixed",
    coefficient_action: CoordinateFieldAction | None = None,
    state_family: str = "spatial_translation",
    parameter_action: ActionRef | None = None,
    equation_relation: str = "same_equation",
    parameter_relation: str = "preserved",
) -> ProblemActionBundle:
    problem = ProblemInstanceSpec(
        equation_family="heat_1d",
        equation_form="nonconservative",
        parameters={"nu_baseline": 0.1},
        coefficient_fields={"nu": _ref(treatment)},
        spatial_axis_name="x",
        time_axis_name="t",
        domain_type="periodic_uniform",
    )
    return ProblemActionBundle(
        problem_instance=problem,
        state_action=_action(
            "state", state_family, **({"offset": 3 * DX} if state_family != "identity" else {})
        ),
        domain_action=_action("domain", "identity"),
        boundary_action=_action("domain", "identity"),
        coefficient_field_actions={
            "nu": coefficient_action or CoordinateFieldAction(family="identity")
        },
        expected_residual_relation=ExpectedResidualRelation(
            equation_relation=equation_relation,
            parameter_relation=parameter_relation,
            coefficient_relation=coefficient_relation,
            domain_relation="preserved",
            boundary_relation="preserved",
            expected_operator=ExpectedResidualOperator(family="identity"),
        ),
        parameter_action=parameter_action,
    )


SHIFT = CoordinateFieldAction(family="shift", parameters={"offset": 3 * DX})
OPPOSED = CoordinateFieldAction(family="shift", parameters={"offset": -3 * DX})


def _branch_bundles() -> dict[str, ProblemActionBundle | None]:
    """One bundle per branch. B-1 is the absence of one."""
    return {
        "B-1": None,
        "B-2": _bundle(),
        "B-3": _bundle(
            treatment="co_transformable_background",
            coefficient_relation="co_transformed",
            coefficient_action=SHIFT,
            equation_relation="equivalence_transformation",
        ),
        "B-4": _bundle(
            treatment="fixed_background",
            coefficient_relation="co_transformed",
            coefficient_action=SHIFT,
            equation_relation="equivalence_transformation",
        ),
        "B-5": _bundle(
            treatment="co_transformable_background",
            coefficient_relation="co_transformed",
            coefficient_action=OPPOSED,
            equation_relation="equivalence_transformation",
        ),
        "B-6": _bundle(
            state_family="identity",
            parameter_action=_action("parameter", "scalar_rescale", factor=2.0),
            parameter_relation="transformed",
        ),
        "B-7": _bundle(
            treatment="unknown",
            coefficient_relation="unknown",
            coefficient_action=SHIFT,
        ),
    }


# --- all seven branches -----------------------------------------------------


@pytest.mark.parametrize("branch", BRANCHES)
def test_every_branch_is_reachable(branch: str) -> None:
    assert classify_branch(_branch_bundles()[branch]) == branch


def test_the_seven_branches_are_distinct() -> None:
    observed = [classify_branch(b) for b in _branch_bundles().values()]
    assert sorted(observed) == sorted(BRANCHES)
    assert len(set(observed)) == 7


# --- blocking happens before discovery, measured ----------------------------


@pytest.mark.parametrize("branch", ["B-4", "B-5", "B-6", "B-7"])
def test_blocked_branches_never_call_the_task(branch: str) -> None:
    """The load-bearing test of this sub-phase.

    ``exploding_task`` raises the moment it is invoked. If any blocked branch
    reaches it, this fails with TaskWasCalled rather than quietly producing a
    well-formed result about a problem nobody asked for.
    """
    report = run_downstream_with_action_bundle(exploding_task, _branch_bundles()[branch])
    assert report["task_was_run"] is False
    assert report["blocked_before_discovery"] is True


def test_zero_task_invocations_across_every_blocked_branch() -> None:
    """Counted, not inferred: the aggregate the spec asks for."""
    calls = 0

    def counting_task() -> dict:
        nonlocal calls
        calls += 1
        return _fake_task_result()

    for branch in ("B-4", "B-5", "B-6", "B-7"):
        run_downstream_with_action_bundle(counting_task, _branch_bundles()[branch])
    assert calls == 0, f"the task ran {calls} times across the blocked branches"


def test_the_sentinel_actually_fires_when_the_task_does_run() -> None:
    """Otherwise the four tests above could pass by never running anything.

    A guard that cannot fail is not a guard, so this proves the sentinel works
    by pointing it at a branch that is supposed to run the task.
    """
    with pytest.raises(TaskWasCalled):
        run_downstream_with_action_bundle(exploding_task, _branch_bundles()["B-2"])


@pytest.mark.parametrize("branch", ["B-4", "B-5", "B-6", "B-7"])
def test_each_block_names_its_own_reason(branch: str) -> None:
    """'invalid' is not actionable; the caller has to know what to fix."""
    report = run_downstream_with_action_bundle(exploding_task, _branch_bundles()[branch])
    status = report["bundle_relation_status"]
    assert status in BLOCK_STATUSES
    expected = {
        "B-4": "blocked_fixed_background_state_mismatch",
        "B-5": "blocked_action_direction_wrong",
        "B-6": "blocked_parameter_only_without_state",
        "B-7": "blocked_coefficient_treatment_unspecified",
    }[branch]
    assert status == expected


def test_the_four_block_statuses_are_distinct() -> None:
    reports = [
        run_downstream_with_action_bundle(exploding_task, _branch_bundles()[b])
        for b in ("B-4", "B-5", "B-6", "B-7")
    ]
    statuses = [r["bundle_relation_status"] for r in reports]
    assert len(set(statuses)) == 4
    assert set(statuses) == set(BLOCK_STATUSES)


# --- the 22-key schema does not move ----------------------------------------


def test_the_frozen_schema_is_still_twenty_two_keys() -> None:
    """Regression against v0.30.1, restated at the v0.37 boundary."""
    assert len(discovery_module._TASK_RESULT_TOP_LEVEL_KEYS) == 22


def test_b1_returns_the_task_payload_unchanged() -> None:
    """No bundle means nothing to say about one. Not wrapped, not coerced."""
    original = _fake_task_result()
    result = run_downstream_with_action_bundle(lambda: original, None)
    assert result == original
    assert result["summary_type"] == "discovery_task_result"
    assert len(result) == 22
    assert "action_bundle_hash" not in result
    assert "bundle_relation_status" not in result


@pytest.mark.parametrize("branch", ["B-2", "B-3"])
def test_augmented_payload_is_exactly_twenty_two_plus_two(branch: str) -> None:
    result = run_downstream_with_action_bundle(_fake_task_result, _branch_bundles()[branch])
    assert len(result) == augmented_key_count(22) == 24
    added = set(result) - set(_fake_task_result())
    assert added == {"action_bundle_hash", "bundle_relation_status"}


@pytest.mark.parametrize("branch", ["B-2", "B-3"])
def test_augmented_payload_uses_a_new_summary_type(branch: str) -> None:
    """A new type on a new payload -- never a variant of the frozen one."""
    result = run_downstream_with_action_bundle(_fake_task_result, _branch_bundles()[branch])
    assert result["summary_type"] == AUGMENTED_TASK_SUMMARY_TYPE
    assert result["summary_type"] != "discovery_task_result"


@pytest.mark.parametrize("branch", ["B-2", "B-3"])
def test_augmentation_preserves_every_frozen_key(branch: str) -> None:
    result = run_downstream_with_action_bundle(_fake_task_result, _branch_bundles()[branch])
    for key in discovery_module._TASK_RESULT_TOP_LEVEL_KEYS:
        if key == "summary_type":
            continue
        assert key in result, key


def test_no_emitted_payload_mutates_the_task_result() -> None:
    """Shape-invariant check across every branch that runs the task."""
    for branch in ("B-1", "B-2", "B-3"):
        original = _fake_task_result()
        snapshot = dict(original)
        # Bound as a default so the closure captures the value, not the loop
        # variable -- otherwise a later refactor that defers the call silently
        # tests the last iteration three times.
        run_downstream_with_action_bundle(
            lambda payload=original: payload, _branch_bundles()[branch]
        )
        assert original == snapshot, f"{branch} mutated the task's own payload"


# --- payload shape ----------------------------------------------------------


@pytest.mark.parametrize("branch", BRANCHES)
def test_every_branch_emits_strict_json(branch: str) -> None:
    result = run_downstream_with_action_bundle(_fake_task_result, _branch_bundles()[branch])
    assert json.loads(json.dumps(result, allow_nan=False)) == result


@pytest.mark.parametrize("branch", ["B-2", "B-3", "B-4", "B-5", "B-6", "B-7"])
def test_every_bundled_branch_reports_a_known_status(branch: str) -> None:
    result = run_downstream_with_action_bundle(_fake_task_result, _branch_bundles()[branch])
    assert result["bundle_relation_status"] in BUNDLE_RELATION_STATUSES


@pytest.mark.parametrize("branch", ["B-2", "B-3", "B-4", "B-5", "B-6", "B-7"])
def test_every_bundled_branch_records_the_bundle_hash(branch: str) -> None:
    bundle = _branch_bundles()[branch]
    result = run_downstream_with_action_bundle(_fake_task_result, bundle)
    assert result["action_bundle_hash"] == bundle.identity()  # type: ignore[union-attr]


# --- one summary type, two shapes, one discriminator ------------------------


def test_bundle_relation_status_discriminates_the_two_shapes() -> None:
    """The same summary_type is emitted in two shapes; this tells them apart.

    Probing for key presence would be the ``*_available`` anti-pattern in
    reverse. A value in BLOCK_STATUSES means the blocked shape, always, and a
    value outside it means the 24-key augmented shape, always.
    """
    for branch in ("B-2", "B-3"):
        result = run_downstream_with_action_bundle(_fake_task_result, _branch_bundles()[branch])
        assert result["bundle_relation_status"] not in BLOCK_STATUSES
        assert len(result) == 24
    for branch in ("B-4", "B-5", "B-6", "B-7"):
        result = run_downstream_with_action_bundle(exploding_task, _branch_bundles()[branch])
        assert result["bundle_relation_status"] in BLOCK_STATUSES
        assert result["blocked_before_discovery"] is True


def test_the_block_and_non_block_status_sets_are_disjoint() -> None:
    """Otherwise the discriminator is ambiguous and both shapes are unreadable."""
    non_block = set(BUNDLE_RELATION_STATUSES) - set(BLOCK_STATUSES)
    assert non_block and set(BLOCK_STATUSES)
    assert non_block.isdisjoint(set(BLOCK_STATUSES))


# --- guards -----------------------------------------------------------------


def test_a_precomputed_result_is_refused() -> None:
    """Ordering is the contract, and a result cannot express ordering."""
    with pytest.raises(ScopeValidationError, match="not a result"):
        run_downstream_with_action_bundle(_fake_task_result(), None)  # type: ignore[arg-type]


def test_a_non_bundle_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="ProblemActionBundle or None"):
        classify_branch({"seed": 1})  # type: ignore[arg-type]


def test_a_task_returning_a_non_result_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="no summary_type"):
        run_downstream_with_action_bundle(lambda: {"nope": 1}, None)


def test_v0_37d_adds_no_root_export() -> None:
    import pdelie

    for name in ("run_downstream_with_action_bundle", "classify_branch"):
        assert name not in pdelie.__all__
