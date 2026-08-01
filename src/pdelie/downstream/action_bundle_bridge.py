"""v0.37d: route a discovery task through a declared action bundle, or refuse to.

Seven branches. One passes through untouched, two augment, and four **block
before any discovery work happens at all**.

Blocking happens before PySINDy, and that is measured
=====================================================

A bundle whose claims are inconsistent describes a problem nobody asked for, and
running discovery on it produces a well-formed result about nothing. So the four
invalid branches return before the task is invoked.

That is not asserted by reading the code. ``tests/test_v0_37d_downstream_crash_test.py``
patches the task entry point to raise on call and asserts it never fires across
the blocked branches. "We are fairly sure it returns early" and "it provably did
not run" are different claims, and only one of them survives a refactor.

The 22-key schema does not move
===============================

``discovery_task_result`` has had a 22-key top level since v0.30.1 and keeps it.
This module **never** edits that payload:

* on B-1 the original dict is returned **by identity**, not copied, not wrapped,
  not re-keyed;
* on B-2/B-3 a *new* summary type is emitted, carrying the same 22 keys plus
  exactly two more.

Twenty-four keys, not twenty-two plus a nested blob, because a consumer that
wants the bundle context should not have to know it is nested somewhere.

One summary type, two shapes, one discriminator
===============================================

``pdelie_downstream_task_with_action_bundle`` is emitted in two shapes: the
24-key augmented result, and a shorter blocked report that has no task result to
augment because the task never ran. Conditional shapes have precedent here --
the weak diagnostic's 27/28-key conditional -- but they are only usable if a
consumer can tell which it holds without probing for key presence.

``bundle_relation_status`` is that discriminator, and it is present in **both**.
It carries a value from :data:`BLOCK_STATUSES` exactly when the payload is the
blocked shape, and never otherwise. A test asserts the two value sets are
disjoint, so the discriminator cannot become ambiguous by someone adding a
status to the wrong list.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from pdelie.actions.action_bundle import ProblemActionBundle
from pdelie.actions.execute import classify_runtime_path
from pdelie.actions.validate import validate_action_bundle
from pdelie.errors import ScopeValidationError

__all__ = [
    "AUGMENTED_TASK_SUMMARY_TYPE",
    "BLOCK_STATUSES",
    "BRANCHES",
    "BUNDLE_RELATION_STATUSES",
    "classify_branch",
    "run_downstream_with_action_bundle",
]

AUGMENTED_TASK_SUMMARY_TYPE = "pdelie_downstream_task_with_action_bundle"

#: The seven branches, frozen.
BRANCHES: tuple[str, ...] = ("B-1", "B-2", "B-3", "B-4", "B-5", "B-6", "B-7")

#: Why a bundle was refused. Each names the inconsistency rather than saying
#: "invalid", because a caller has to be able to fix it.
BLOCK_STATUSES: tuple[str, ...] = (
    "blocked_fixed_background_state_mismatch",
    "blocked_action_direction_wrong",
    "blocked_parameter_only_without_state",
    "blocked_coefficient_treatment_unspecified",
)

#: What the emitted payload may report. The non-blocked values are the v0.37b
#: observed-relation vocabulary; blocking adds four.
BUNDLE_RELATION_STATUSES: tuple[str, ...] = (
    "confirmed",
    "violated",
    "inconclusive",
    "no_relation_declared",
    *BLOCK_STATUSES,
)

#: Exactly the two keys the augmented payload adds. Frozen: the whole point is
#: that 22 + 2 = 24 and nothing else moved.
_ADDED_KEYS: tuple[str, ...] = ("action_bundle_hash", "bundle_relation_status")


def _blocking_reason(bundle: ProblemActionBundle) -> str | None:
    """Which block applies, or None if the bundle is coherent.

    Order matters: a bundle can be wrong in more than one way, and the first
    reason reported should be the most specific one a caller can act on.
    """
    relation = bundle.expected_residual_relation
    fields = bundle.problem_instance.coefficient_fields
    actions = bundle.coefficient_field_actions

    # B-7 -- a coefficient field is present but its treatment was never declared.
    # Checked first: without a treatment the other checks cannot be evaluated.
    for name, reference in fields.items():
        if reference.treatment == "unknown" and not actions[name].is_identity:
            return "blocked_coefficient_treatment_unspecified"

    # B-4 -- the state is claimed to move against a background declared fixed,
    # while the relation claims the coefficient co-transformed. The v0.34b
    # non-equivalence case, declared as if it were an equivalence.
    if relation.coefficient_relation == "co_transformed":
        for name, reference in fields.items():
            if reference.treatment == "fixed_background" and not actions[name].is_identity:
                return "blocked_fixed_background_state_mismatch"

    # B-5 -- the coefficient moves opposite the state. Runtime path P-4.
    try:
        if classify_runtime_path(bundle) == "P-4":
            return "blocked_action_direction_wrong"
    except ScopeValidationError:
        # An unclassifiable bundle is not one of the four named blocks; the
        # rule table below is the authority on whether it is legal at all.
        pass

    # B-6 -- a parameter action with no state action. Rescaling a parameter
    # without transforming the state it multiplies is not a symmetry claim.
    if bundle.parameter_action is not None and bundle.state_action.action_family == "identity":
        return "blocked_parameter_only_without_state"

    return None


def classify_branch(bundle: ProblemActionBundle | None) -> str:
    """Which of the seven branches this bundle takes."""
    if bundle is None:
        return "B-1"
    if not isinstance(bundle, ProblemActionBundle):
        raise ScopeValidationError("bundle must be a ProblemActionBundle or None.")

    reason = _blocking_reason(bundle)
    if reason == "blocked_fixed_background_state_mismatch":
        return "B-4"
    if reason == "blocked_action_direction_wrong":
        return "B-5"
    if reason == "blocked_parameter_only_without_state":
        return "B-6"
    if reason == "blocked_coefficient_treatment_unspecified":
        return "B-7"
    return "B-3" if bundle.expected_residual_relation.coefficient_relation == "co_transformed" else "B-2"


def _validated_task_result(result: object) -> Mapping[str, Any]:
    if not isinstance(result, Mapping):
        raise ScopeValidationError("the task must return a mapping.")
    if "summary_type" not in result:
        raise ScopeValidationError(
            "the task result carries no summary_type; it is not a discovery result."
        )
    return result


def run_downstream_with_action_bundle(
    run_task: Callable[[], Mapping[str, Any]],
    bundle: ProblemActionBundle | None = None,
) -> dict[str, Any]:
    """Run a discovery task under a declared bundle, or block before running it.

    ``run_task`` is a zero-argument callable producing a ``discovery_task_result``.
    It is a callable rather than a result so that **blocking can happen before it
    is invoked** -- passing an already-computed result would make the ordering
    unobservable, and the ordering is the contract.

    On B-1 the task's own payload is returned **by identity**. It is not copied
    and not wrapped: a caller who passes no bundle gets back exactly what the
    task produced.
    """
    if not callable(run_task):
        raise ScopeValidationError(
            "run_task must be a zero-argument callable, not a result. Blocking "
            "happens before the task runs, which a precomputed result cannot "
            "express."
        )
    branch = classify_branch(bundle)

    # --- blocked branches: return before run_task is ever called ------------
    if branch in ("B-4", "B-5", "B-6", "B-7"):
        # No assert: it is stripped under -O, and this is the branch that must
        # not fall through to run_task under any interpreter flag.
        if bundle is None:  # pragma: no cover - classify_branch cannot produce this
            raise ScopeValidationError(f"branch {branch} without a bundle is impossible.")
        status = _blocking_reason(bundle)
        if status is None:  # pragma: no cover - same
            raise ScopeValidationError(f"branch {branch} without a block reason.")
        return {
            "summary_type": AUGMENTED_TASK_SUMMARY_TYPE,
            "summary_schema_version": "0.1",
            "branch": branch,
            "bundle_relation_status": status,
            "action_bundle_hash": bundle.identity(),
            "task_was_run": False,
            "blocked_before_discovery": True,
            "diagnostic_only": True,
        }

    # --- B-1: no bundle, nothing to say about one ---------------------------
    if branch == "B-1":
        return dict(_validated_task_result(run_task()))

    # --- B-2 / B-3: the bundle is coherent, so the task runs ---------------
    if bundle is None:  # pragma: no cover - B-1 is the only bundle-less branch
        raise ScopeValidationError("a non-B-1 branch requires a bundle.")
    validate_action_bundle(bundle)
    result = _validated_task_result(run_task())

    augmented = dict(result)
    augmented["summary_type"] = AUGMENTED_TASK_SUMMARY_TYPE
    augmented["action_bundle_hash"] = bundle.identity()
    augmented["bundle_relation_status"] = (
        "no_relation_declared"
        if not bundle.expected_residual_relation.permits_confirmation
        else "inconclusive"
    )
    return augmented


def augmented_key_count(task_result_key_count: int) -> int:
    """What the augmented payload's top level must contain. Frozen at +2."""
    return task_result_key_count + len(_ADDED_KEYS)
