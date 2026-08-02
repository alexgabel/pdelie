"""v0.37a: a declared action on a problem, and what it claims about the residual.

Contracts only; the executor is v0.37b.

Five independent relation axes
==============================

:class:`ExpectedResidualRelation` carries five axes, not one collapsed
``relation_type``. Boundary preservation is orthogonal to equation equivalence:
a transformation can be an equivalence transformation with the boundary
preserved, or an equivalence transformation with the boundary destroyed, and a
single enum cannot say which. The axes mirror
:class:`~pdelie.actions.problem_action_spec.ProblemActionSpec` exactly, so a
bundle and a spec describe the same claim in the same words.

An earlier draft collapsed them and then needed a rule coupling
``boundary_action`` back to the collapsed value. With independent axes that
coupling does not exist and the rule is not needed.

Operator: one field, not two
============================

``family`` and ``parameters`` are meaningless apart -- a family without its
parameters cannot be validated, and parameters without a family cannot be
interpreted. :class:`ExpectedResidualOperator` holds them together so the pair
is inseparable by construction, and every family declares its own parameter
shape. An empty shape is a real shape: ``identity`` and ``diagnostic_fitted``
genuinely have nothing to declare in advance.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from pdelie.actions.action_ref import ActionRef
from pdelie.actions.parameter_action_spec import (
    ParameterActionSpec,
    as_parameter_action_spec,
)
from pdelie.actions.problem_spec import (
    CoordinateFieldAction,
    ProblemInstanceSpec,
    _require_json_scalar,
)
from pdelie.artifact.semantic_hash import semantic_hash
from pdelie.errors import ScopeValidationError

__all__ = [
    "BOUNDARY_RELATIONS",
    "BUNDLE_SCHEMA_VERSION",
    "COEFFICIENT_RELATIONS",
    "DERIVATIVE_NAMES",
    "DOMAIN_RELATIONS",
    "EQUATION_RELATIONS",
    "EXPECTED_OPERATOR_FAMILIES",
    "OBSERVED_RELATION_STATUSES",
    "PARAMETER_RELATIONS",
    "ExpectedResidualOperator",
    "ExpectedResidualRelation",
    "ProblemActionBundle",
]

BUNDLE_SCHEMA_VERSION = "0.1"

#: The five axes. Identical to ``ProblemActionSpec``'s, deliberately.
EQUATION_RELATIONS: tuple[str, ...] = (
    "same_equation",
    "equivalence_transformation",
    "equation_invalid",
    "unknown",
)
PARAMETER_RELATIONS: tuple[str, ...] = ("preserved", "transformed", "not_applicable", "unknown")
COEFFICIENT_RELATIONS: tuple[str, ...] = (
    "fixed",
    "co_transformed",
    "not_applicable",
    "unknown",
)
DOMAIN_RELATIONS: tuple[str, ...] = ("preserved", "overlap_crop", "not_preserved", "unknown")
BOUNDARY_RELATIONS: tuple[str, ...] = (
    "preserved",
    "interior_only",
    "not_preserved",
    "unknown",
)

#: Derivative names a ``linear_combination_of_derivatives`` operator may use.
#:
#: This is the measured union of ``_REQUIRED_DERIVATIVES`` across all five
#: residual evaluators, not a fresh vocabulary. The pattern is ``u_`` followed by
#: ``t`` or by ``x`` repeated to the derivative order. Free-form keys would make
#: ``{"u_xx": 0.1}`` and ``{"uxx": 0.1}`` equally acceptable while only one means
#: anything.
#:
#: The ``(t, x)`` axis naming is hardcoded, which is correct for v0.37's scalar
#: 1-D scope. Custom axis names arrive with named-axis discipline at v0.40.
DERIVATIVE_NAMES: tuple[str, ...] = ("u_t", "u_x", "u_xx", "u_xxx")

#: The form of the relation between the original and transformed residual.
EXPECTED_OPERATOR_FAMILIES: tuple[str, ...] = (
    "identity",
    "scalar_multiplier",
    "affine",
    "linear_combination_of_derivatives",
    "diagnostic_fitted",
)

#: What measurement observed. Extends the four-value set in
#: ``docs/planning/V0_37_BINDING_DESIGN_CONSTRAINTS.md`` C-4 by exactly one
#: value.
#:
#: ``no_relation_declared`` is not ``inconclusive``: inconclusive means the
#: measurement was attempted and could not decide, whereas this means there was
#: never a decision to make. It is deliberately **not** spelled
#: ``diagnostic_only`` -- that string is already a boolean payload flag in 24
#: emissions across 16 modules, meaning "this payload makes no numerical claim",
#: and one word carrying two roles is how vocabularies rot.
OBSERVED_RELATION_STATUSES: tuple[str, ...] = (
    "confirmed",
    "violated",
    "inconclusive",
    "blocked",
    "no_relation_declared",
)

#: Families whose relation is *declared* and can therefore be confirmed or
#: violated. ``diagnostic_fitted`` is absent: nothing is declared, so a fit is
#: exploration rather than a check, and there is nothing for it to contradict.
DECLARED_OPERATOR_FAMILIES: frozenset[str] = frozenset(
    {"identity", "scalar_multiplier", "affine", "linear_combination_of_derivatives"}
)


def _require_float(value: object, *, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ScopeValidationError(f"{where} must be a real number; got {type(value).__name__}.")
    number = float(value)
    if not math.isfinite(number):
        raise ScopeValidationError(f"{where} must be finite; got {number!r}.")
    return number


@dataclass(frozen=True)
class ExpectedResidualOperator:
    """The declared form of ``R'`` in terms of ``R``, with its parameters.

    Rules R-A12a through R-A12e, one per family. Each family's parameter set is
    closed, so ``parameters`` is a contract rather than an escape hatch.
    """

    family: str
    parameters: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.family not in EXPECTED_OPERATOR_FAMILIES:
            raise ScopeValidationError(
                f"family {self.family!r} is not one of {list(EXPECTED_OPERATOR_FAMILIES)}."
            )
        if not isinstance(self.parameters, Mapping):
            raise ScopeValidationError("parameters must be a mapping.")
        parameters = dict(self.parameters)
        _require_json_scalar(parameters, where="ExpectedResidualOperator.parameters")

        # R-A12a -- identity: R'(u) = R(u). Nothing to declare.
        if self.family == "identity":
            if parameters:
                raise ScopeValidationError(
                    f"identity declares no parameters; got {sorted(parameters)}. An "
                    f"empty mapping is the shape, not a placeholder."
                )
        # R-A12b -- scalar_multiplier: R'(u) = c * R(u).
        elif self.family == "scalar_multiplier":
            if set(parameters) != {"multiplier"}:
                raise ScopeValidationError(
                    f"scalar_multiplier declares exactly {{'multiplier'}}; got "
                    f"{sorted(parameters)}."
                )
            parameters["multiplier"] = _require_float(
                parameters["multiplier"], where="multiplier"
            )
        # R-A12c -- affine: R'(u) = a * R(u) + b, with b zero-order.
        elif self.family == "affine":
            if set(parameters) != {"multiplier", "offset"}:
                raise ScopeValidationError(
                    f"affine declares exactly {{'multiplier', 'offset'}}; got "
                    f"{sorted(parameters)}."
                )
            for key in ("multiplier", "offset"):
                parameters[key] = _require_float(parameters[key], where=key)
        # R-A12d -- linear_combination_of_derivatives.
        elif self.family == "linear_combination_of_derivatives":
            if set(parameters) != {"coefficients"}:
                raise ScopeValidationError(
                    f"linear_combination_of_derivatives declares exactly "
                    f"{{'coefficients'}}; got {sorted(parameters)}."
                )
            coefficients = parameters["coefficients"]
            if not isinstance(coefficients, Mapping) or not coefficients:
                raise ScopeValidationError("coefficients must be a non-empty mapping.")
            unknown = sorted(set(coefficients) - set(DERIVATIVE_NAMES))
            if unknown:
                raise ScopeValidationError(
                    f"coefficients names {unknown}, which are not in the frozen "
                    f"derivative vocabulary {list(DERIVATIVE_NAMES)}. That vocabulary "
                    f"is the measured union across the five residual evaluators; "
                    f"extending it is a deliberate act, not a typo."
                )
            parameters["coefficients"] = {
                name: _require_float(value, where=f"coefficients[{name!r}]")
                for name, value in coefficients.items()
            }
        # R-A12e -- diagnostic_fitted: nothing declared ahead of time.
        else:
            if parameters:
                raise ScopeValidationError(
                    f"diagnostic_fitted declares no parameters; got {sorted(parameters)}. "
                    f"What a fit produces belongs in the report's optional_evidence, "
                    f"not in a declaration -- parameters are what you declare, not "
                    f"what you fit."
                )
        object.__setattr__(self, "parameters", parameters)

    @property
    def is_declared(self) -> bool:
        """Whether this family states a relation that measurement can contradict."""
        return self.family in DECLARED_OPERATOR_FAMILIES

    def as_dict(self) -> dict[str, Any]:
        return {"family": self.family, "parameters": dict(self.parameters)}


@dataclass(frozen=True)
class ExpectedResidualRelation:
    """What the transformation claims about the residual, on five axes."""

    equation_relation: str
    parameter_relation: str
    coefficient_relation: str
    domain_relation: str
    boundary_relation: str
    expected_operator: ExpectedResidualOperator
    #: Unset at v0.37a by design. Filled at the v0.37c confirmatory freeze, after
    #: the pilot measures what the tolerances should be.
    tolerance_declaration: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        for name, allowed in (
            ("equation_relation", EQUATION_RELATIONS),
            ("parameter_relation", PARAMETER_RELATIONS),
            ("coefficient_relation", COEFFICIENT_RELATIONS),
            ("domain_relation", DOMAIN_RELATIONS),
            ("boundary_relation", BOUNDARY_RELATIONS),
        ):
            value = getattr(self, name)
            if value not in allowed:
                raise ScopeValidationError(f"{name} {value!r} is not one of {list(allowed)}.")
        if not isinstance(self.expected_operator, ExpectedResidualOperator):
            raise ScopeValidationError(
                "expected_operator must be an ExpectedResidualOperator; family and "
                "parameters are validated as a pair and cannot be supplied apart."
            )
        if self.tolerance_declaration is not None:
            if not isinstance(self.tolerance_declaration, Mapping):
                raise ScopeValidationError("tolerance_declaration must be a mapping or None.")
            _require_json_scalar(self.tolerance_declaration, where="tolerance_declaration")
            object.__setattr__(self, "tolerance_declaration", dict(self.tolerance_declaration))

    @property
    def permits_confirmation(self) -> bool:
        """R-A13: whether a run of this relation could ever be confirmed.

        ``diagnostic_fitted`` declares nothing, so a fit against it is
        exploration rather than a check. Its only honest observed status is
        ``no_relation_declared``.
        """
        return self.expected_operator.is_declared

    def allowed_observed_statuses(self) -> tuple[str, ...]:
        """The statuses a v0.37b run of this relation may legally report."""
        if self.permits_confirmation:
            return ("confirmed", "violated", "inconclusive", "blocked")
        return ("no_relation_declared", "blocked")

    def as_dict(self) -> dict[str, Any]:
        return {
            "equation_relation": self.equation_relation,
            "parameter_relation": self.parameter_relation,
            "coefficient_relation": self.coefficient_relation,
            "domain_relation": self.domain_relation,
            "boundary_relation": self.boundary_relation,
            "expected_operator": self.expected_operator.as_dict(),
            "tolerance_declaration": (
                None
                if self.tolerance_declaration is None
                else dict(self.tolerance_declaration)
            ),
        }


@dataclass(frozen=True)
class ProblemActionBundle:
    """A problem, the actions applied to it, and what they claim.

    It carries **no seed**. A seed is not a property of a mathematical action;
    it belongs to :class:`~pdelie.actions.execution_config.ActionExecutionConfig`,
    per constraint C-1. Two bundles identical in every mathematical respect must
    hash identically, and they cannot if a number nobody used is folded in.
    """

    problem_instance: ProblemInstanceSpec
    state_action: ActionRef
    domain_action: ActionRef
    boundary_action: ActionRef
    coefficient_field_actions: Mapping[str, CoordinateFieldAction]
    expected_residual_relation: ExpectedResidualRelation
    parameter_action: ParameterActionSpec | ActionRef | None = None
    bundle_version: str = BUNDLE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.problem_instance, ProblemInstanceSpec):
            raise ScopeValidationError("problem_instance must be a ProblemInstanceSpec.")
        for name in ("state_action", "domain_action", "boundary_action"):
            value = getattr(self, name)
            if not isinstance(value, ActionRef):
                raise ScopeValidationError(f"{name} must be an ActionRef.")
        # v0.38: normalised to the typed form at construction, so exactly one
        # representation reaches anything downstream. An ActionRef carrying a
        # `target_parameters` key is upgraded rather than refused, so v0.38e
        # call sites keep working.
        if self.parameter_action is not None:
            spec = as_parameter_action_spec(self.parameter_action)
            if spec.target_parameters is not None:
                known = set(self.problem_instance.parameters)
                unknown = sorted(set(spec.target_parameters) - known)
                if unknown:
                    raise ScopeValidationError(
                        f"parameter_action targets {unknown}, which are not "
                        f"parameters of this problem ({sorted(known)}). A target "
                        f"that does not exist cannot be acted on, and ignoring it "
                        f"would rescale nothing while reporting success."
                    )
            object.__setattr__(self, "parameter_action", spec)
        if not isinstance(self.expected_residual_relation, ExpectedResidualRelation):
            raise ScopeValidationError(
                "expected_residual_relation must be an ExpectedResidualRelation."
            )
        if self.bundle_version != BUNDLE_SCHEMA_VERSION:
            raise ScopeValidationError(f"bundle_version must be {BUNDLE_SCHEMA_VERSION!r}.")

        if not isinstance(self.coefficient_field_actions, Mapping):
            raise ScopeValidationError("coefficient_field_actions must be a mapping.")
        actions: dict[str, CoordinateFieldAction] = {}
        declared = set(self.problem_instance.coefficient_fields)
        for key, action in self.coefficient_field_actions.items():
            if not isinstance(action, CoordinateFieldAction):
                raise ScopeValidationError(
                    f"coefficient_field_actions[{key!r}] is {type(action).__name__}, "
                    f"not a CoordinateFieldAction."
                )
            if key not in declared:
                raise ScopeValidationError(
                    f"coefficient_field_actions names {key!r}, which the problem "
                    f"instance does not declare. Known fields: {sorted(declared)}."
                )
            actions[key] = action
        missing = sorted(declared - set(actions))
        if missing:
            raise ScopeValidationError(
                f"coefficient_field_actions omits {missing}. Every declared field "
                f"needs an action -- use family='identity' to say it is untouched, "
                f"because silence and 'left alone' are different claims."
            )
        object.__setattr__(self, "coefficient_field_actions", actions)
        semantic_hash(self.as_dict())

    @property
    def parameter_action_spec(self) -> ParameterActionSpec | None:
        """The parameter action in its one canonical form.

        The field accepts a ``ParameterActionSpec`` or a legacy ``ActionRef``
        and normalises to the former in ``__post_init__``. This accessor is
        typed to the stored form, so readers narrow once here rather than at
        every call site -- and a reader cannot accidentally consume the legacy
        shape, because by this point none exists.
        """
        action = self.parameter_action
        if action is None:
            return None
        assert isinstance(action, ParameterActionSpec)
        return action

    def identity(self) -> str:
        return semantic_hash(self.as_dict())

    def as_dict(self) -> dict[str, Any]:
        return {
            "problem_instance": self.problem_instance.as_dict(),
            "state_action": self.state_action.as_dict(),
            "parameter_action": (
                None if self.parameter_action is None else self.parameter_action.as_dict()
            ),
            "coefficient_field_actions": {
                name: action.as_dict()
                for name, action in self.coefficient_field_actions.items()
            },
            "domain_action": self.domain_action.as_dict(),
            "boundary_action": self.boundary_action.as_dict(),
            "expected_residual_relation": self.expected_residual_relation.as_dict(),
            "bundle_version": self.bundle_version,
        }
