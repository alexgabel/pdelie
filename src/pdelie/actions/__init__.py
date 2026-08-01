"""v0.36b: problem-action contracts and their legality rules. Submodule-only."""

from __future__ import annotations

from pdelie.actions.action_bundle import (
    BUNDLE_SCHEMA_VERSION,
    DERIVATIVE_NAMES,
    EXPECTED_OPERATOR_FAMILIES,
    OBSERVED_RELATION_STATUSES,
    ExpectedResidualOperator,
    ExpectedResidualRelation,
    ProblemActionBundle,
)
from pdelie.actions.action_ref import ACTION_TARGETS, ActionRef
from pdelie.actions.execution_config import (
    INTERPOLATION_BACKENDS,
    ActionExecutionConfig,
)
from pdelie.actions.interaction_rules import RULE_COUNT, RULES, InteractionRule
from pdelie.actions.problem_action_spec import (
    BOUNDARY_RELATIONS,
    COEFFICIENT_RELATIONS,
    DOMAIN_RELATIONS,
    EQUATION_RELATIONS,
    PARAMETER_RELATIONS,
    ProblemActionSpec,
    validate_action_spec,
)
from pdelie.actions.problem_spec import (
    COEFFICIENT_TREATMENTS,
    COORDINATE_FIELD_ACTION_FAMILIES,
    DOMAIN_TYPES,
    EQUATION_FAMILIES,
    EQUATION_FORMS,
    CoefficientFieldRef,
    CoordinateFieldAction,
    ProblemInstanceSpec,
)
from pdelie.actions.validate import (
    BUNDLE_RULE_COUNT,
    BUNDLE_RULE_IDS,
    BUNDLE_RULES,
    InconsistentBundleError,
    validate_action_bundle,
)

__all__ = [
    "ACTION_TARGETS",
    "BOUNDARY_RELATIONS",
    "BUNDLE_RULES",
    "BUNDLE_RULE_COUNT",
    "BUNDLE_RULE_IDS",
    "BUNDLE_SCHEMA_VERSION",
    "COEFFICIENT_RELATIONS",
    "COEFFICIENT_TREATMENTS",
    "COORDINATE_FIELD_ACTION_FAMILIES",
    "DERIVATIVE_NAMES",
    "DOMAIN_RELATIONS",
    "DOMAIN_TYPES",
    "EQUATION_FAMILIES",
    "EQUATION_FORMS",
    "EQUATION_RELATIONS",
    "EXPECTED_OPERATOR_FAMILIES",
    "INTERPOLATION_BACKENDS",
    "OBSERVED_RELATION_STATUSES",
    "PARAMETER_RELATIONS",
    "RULES",
    "RULE_COUNT",
    "ActionExecutionConfig",
    "ActionRef",
    "CoefficientFieldRef",
    "CoordinateFieldAction",
    "ExpectedResidualOperator",
    "ExpectedResidualRelation",
    "InconsistentBundleError",
    "InteractionRule",
    "ProblemActionBundle",
    "ProblemActionSpec",
    "ProblemInstanceSpec",
    "validate_action_bundle",
    "validate_action_spec",
]
