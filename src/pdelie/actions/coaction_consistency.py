"""v0.38e: does the execution do what the bundle declared?

Emits ``pdelie_action_coaction_consistency`` -- a new ``summary_type`` on a new
payload from a new function. The 22-key ``discovery_task_result`` schema is
untouched; this nests, it does not mutate.

What it is for
==============

v0.37.1 fixed one benchmark runner that executed a state rescale while its
bundle declared a parameter rescale. The fix was correct and specific. This
module is the general form: a bookkeeping check that the action a bundle
*declares* is the action an executor would *consume*.

The defect that motivated it
============================

``ActionRef`` has no field naming which parameter a ``scalar_rescale`` targets,
so :func:`~pdelie.actions.execute.execute_bundle` applied the factor to every
numeric parameter. Measured on a two-parameter problem, a rescale meant for the
viscosity also tripled the advection speed.

No v0.37c case could see it: each declares exactly one numeric parameter, and on
a one-element population "rescale all" and "rescale the declared one" are the
same function.

This is the C-5 class one layer down. C-5 was an executor disagreeing with a
declaration. Here the declaration is *incomplete* -- it cannot express a target
-- so the executor supplies one by convention and there is nothing to disagree
with. An audit looking for disagreement finds none.

Status and diagnosis are separate axes
======================================

``target_ambiguous`` is reported as **indeterminate**, not inconsistent. Nothing
has disagreed; the question cannot be answered from what the bundle carries.
Calling it a disagreement would overstate the observation, and the whole reason
this module exists is that overstated observations are expensive.

Rules CR-1 .. CR-8 are frozen in ``docs/design/v0_38e_hypothesis_freeze.md``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from pdelie.actions.action_bundle import ProblemActionBundle
from pdelie.artifact.semantic_hash import semantic_hash
from pdelie.errors import ScopeValidationError

__all__ = [
    "COACTION_CONSISTENCY_SCHEMA_KEYS",
    "COACTION_CONSISTENCY_SUMMARY_TYPE",
    "COACTION_DIAGNOSES",
    "COACTION_STATUSES",
    "LEGAL_STATUS_DIAGNOSIS_PAIRS",
    "PARAMETER_TARGET_KEY",
    "RESERVED_UNREACHABLE_PAIRS",
    "declared_parameter_targets",
    "summarize_coaction_consistency",
]

COACTION_CONSISTENCY_SUMMARY_TYPE = "pdelie_action_coaction_consistency"

#: The key a parameter action may carry to name what it acts on. Optional, so
#: every shipped bundle stays valid; when absent on a multi-parameter problem
#: the target is genuinely ambiguous and is reported as such.
PARAMETER_TARGET_KEY = "target_parameters"

#: CR-1: exactly sixteen, in this order.
COACTION_CONSISTENCY_SCHEMA_KEYS: tuple[str, ...] = (
    "summary_type",
    "summary_schema_version",
    "bundle_identity",
    "runtime_path",
    "consistency_status",
    "diagnosis",
    "diagnosis_detail",
    "declared_state_action_family",
    "declared_parameter_action_family",
    "declared_coefficient_action_families",
    "parameter_target_declaration",
    "parameter_target_candidates",
    "parameter_targets_resolved",
    "coefficient_fields_declared",
    "scientific_payload_hash",
    "execution_metadata",
)

COACTION_STATUSES: tuple[str, ...] = (
    "consistent",
    "inconsistent",
    "not_applicable",
    "indeterminate",
)

COACTION_DIAGNOSES: tuple[str, ...] = (
    "declaration_and_execution_agree",
    "declared_not_executed",
    "executed_not_declared",
    "target_ambiguous",
)

#: CR-4: the pairs that can occur. Everything else is refused at construction
#: rather than emitted -- a report that can say "consistent, but the targets
#: were ambiguous" is a report nobody can act on.
LEGAL_STATUS_DIAGNOSIS_PAIRS: frozenset[tuple[str, str]] = frozenset(
    {
        ("consistent", "declaration_and_execution_agree"),
        ("inconsistent", "declared_not_executed"),
        ("inconsistent", "executed_not_declared"),
        ("indeterminate", "target_ambiguous"),
        ("not_applicable", "declaration_and_execution_agree"),
    }
)

#: Pairs that are legal vocabulary but that no code path can currently emit.
#:
#: v0.38e pilot run 1 BLOCKED on this (criterion B-1). ``executed_not_declared``
#: sat in the legal table, which reads as a claim it can occur -- and nothing
#: could produce it, so the vocabulary advertised a distinction the report had
#: never drawn.
#:
#: It is reserved rather than deleted because it names the PRE-v0.38e behaviour
#: exactly: the executor applied a rescale to a parameter no declaration
#: mentioned. If a future executor path reintroduces that divergence, the report
#: must have a name for it; deleting the vocabulary would leave a future defect
#: unnameable.
#:
#: ``test_reserved_pairs_are_genuinely_unreachable`` parses the branches of
#: :func:`summarize_coaction_consistency` and fails if one ever emits this,
#: so lifting the reservation is a deliberate act rather than a drift.
RESERVED_UNREACHABLE_PAIRS: frozenset[tuple[str, str]] = frozenset(
    {("inconsistent", "executed_not_declared")}
)

#: How the target was declared. Three states, kept distinct: "absent" on a
#: single-parameter problem is unambiguous, and calling it "not_applicable"
#: would lose the fact that a target could have been named and was not.
PARAMETER_TARGET_DECLARATIONS: tuple[str, ...] = ("explicit", "absent", "not_applicable")


def _numeric_parameter_names(bundle: ProblemActionBundle) -> tuple[str, ...]:
    """Parameters a scalar rescale could act on, in sorted order.

    Booleans are excluded: ``bool`` is a subclass of ``int`` in Python, and a
    flag rescaled by 2.0 is not a quantity anyone declared an action on.
    """
    return tuple(
        sorted(
            name
            for name, value in bundle.problem_instance.parameters.items()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        )
    )


def declared_parameter_targets(bundle: ProblemActionBundle) -> tuple[str, ...] | None:
    """Which parameters the bundle's parameter action names, if it names any.

    Returns ``None`` when no target is declared -- distinct from ``()``, which
    would mean "declared, and empty". The caller must not conflate them: one is
    an omission and the other is a statement.
    """
    action = bundle.parameter_action
    if action is None:
        return None
    raw = action.parameters.get(PARAMETER_TARGET_KEY)
    if raw is None:
        return None
    if isinstance(raw, str) or not isinstance(raw, (list, tuple)):
        raise ScopeValidationError(
            f"{PARAMETER_TARGET_KEY} must be a sequence of parameter names, not "
            f"{type(raw).__name__}. A bare string would silently iterate as "
            f"characters."
        )
    names = tuple(str(name) for name in raw)
    if not names:
        raise ScopeValidationError(
            f"{PARAMETER_TARGET_KEY} is empty. An action targeting nothing is not "
            f"an action; omit the key if there is no target to name."
        )
    if len(set(names)) != len(names):
        raise ScopeValidationError(f"{PARAMETER_TARGET_KEY} repeats a name: {names}.")
    known = set(bundle.problem_instance.parameters)
    unknown = sorted(set(names) - known)
    if unknown:
        raise ScopeValidationError(
            f"{PARAMETER_TARGET_KEY} names {unknown}, which are not parameters of "
            f"this problem ({sorted(known)}). A target that does not exist cannot "
            f"be acted on, and silently ignoring it would rescale nothing while "
            f"reporting success."
        )
    return tuple(sorted(names))


def summarize_coaction_consistency(
    bundle: ProblemActionBundle,
    *,
    runtime_path: str | None = None,
    execution_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Report whether the bundle's declaration determines what an executor does.

    This does **not** execute anything, deliberately. A report that only exists
    after a successful execution can never describe the case where execution
    should be refused -- which is the case this module was written for.

    CR-8: it decides no scientific verdict. Whether a transformation *should*
    have preserved a residual is the commutation report's question. This one
    answers whether the declaration says what was going to be done.
    """
    if not isinstance(bundle, ProblemActionBundle):
        raise ScopeValidationError("summarize_coaction_consistency requires a bundle.")

    candidates = _numeric_parameter_names(bundle)
    targets = declared_parameter_targets(bundle)
    parameter_action = bundle.parameter_action

    if parameter_action is None:
        target_declaration = "not_applicable"
    elif targets is None:
        target_declaration = "absent"
    else:
        target_declaration = "explicit"

    resolved: tuple[str, ...] | None
    status: str
    diagnosis: str
    detail: str

    if parameter_action is None:
        resolved = None
        status, diagnosis = "not_applicable", "declaration_and_execution_agree"
        detail = "No parameter action is declared, so there is nothing to reconcile."
    elif targets is not None:
        resolved = targets
        status, diagnosis = "consistent", "declaration_and_execution_agree"
        detail = (
            f"The parameter action names {list(targets)} explicitly, so the "
            f"declaration determines what an executor acts on."
        )
    elif len(candidates) == 1:
        resolved = candidates
        status, diagnosis = "consistent", "declaration_and_execution_agree"
        detail = (
            f"No target is named, but {candidates[0]!r} is the only numeric "
            f"parameter, so the declaration is unambiguous by exhaustion. Naming "
            f"a target would make it unambiguous by construction."
        )
    elif not candidates:
        resolved = None
        status, diagnosis = "inconsistent", "declared_not_executed"
        detail = (
            "A parameter action is declared, but the problem has no numeric "
            "parameter for it to act on, so nothing would be executed."
        )
    else:
        resolved = None
        status, diagnosis = "indeterminate", "target_ambiguous"
        detail = (
            f"The parameter action declares family "
            f"{parameter_action.action_family!r} with no {PARAMETER_TARGET_KEY}, "
            f"and {len(candidates)} numeric parameters are candidates: "
            f"{list(candidates)}. Which of them the action targets cannot be "
            f"decided from the bundle. This is indeterminate rather than "
            f"inconsistent: nothing has disagreed, the question is unanswerable."
        )

    if (status, diagnosis) not in LEGAL_STATUS_DIAGNOSIS_PAIRS:  # pragma: no cover
        raise ScopeValidationError(
            f"({status!r}, {diagnosis!r}) is not a legal pair; CR-4 refuses it."
        )

    scientific_payload = {
        "consistency_status": status,
        "diagnosis": diagnosis,
        "declared_state_action_family": bundle.state_action.action_family,
        "declared_parameter_action_family": (
            None if parameter_action is None else parameter_action.action_family
        ),
        "declared_coefficient_action_families": {
            name: action.family
            for name, action in sorted(bundle.coefficient_field_actions.items())
        },
        "parameter_target_declaration": target_declaration,
        "parameter_target_candidates": list(candidates),
        "parameter_targets_resolved": None if resolved is None else list(resolved),
    }

    payload: dict[str, Any] = {
        "summary_type": COACTION_CONSISTENCY_SUMMARY_TYPE,
        "summary_schema_version": "0.1",
        "bundle_identity": bundle.identity(),
        "runtime_path": runtime_path,
        **scientific_payload,
        "diagnosis_detail": detail,
        "coefficient_fields_declared": sorted(bundle.problem_instance.coefficient_fields),
        # CR-5: the scientific subset is hashed; execution metadata is not, so
        # rerunning on a different machine does not change the hash of what was
        # scientifically observed.
        "scientific_payload_hash": semantic_hash(scientific_payload),
        "execution_metadata": dict(execution_metadata or {}),
    }
    payload = {key: payload[key] for key in COACTION_CONSISTENCY_SCHEMA_KEYS}

    if tuple(payload) != COACTION_CONSISTENCY_SCHEMA_KEYS:  # pragma: no cover
        raise ScopeValidationError("payload keys do not match the frozen schema.")
    # CR-7: strict JSON. A NaN would serialise to a token no strict parser reads.
    json.dumps(payload, allow_nan=False, sort_keys=True)
    return payload
