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
from pdelie.actions.commutation_report import (
    BENCHMARK_OUTCOMES,
    COMMUTATION_REPORT_SUMMARY_TYPE,
    EXPECTED_CASES,
    build_residual_commutation_report,
)
from pdelie.actions.diagnostic_fit import (
    FittedOperatorDiagnostic,
    fit_diagnostic_operator,
)
from pdelie.actions.execute import (
    RUNTIME_PATHS,
    BundleExecutionResult,
    classify_runtime_path,
    execute_bundle,
    execute_coefficient_action,
    execute_state_action,
    shift_cells,
)
from pdelie.actions.execution_config import (
    INTERPOLATION_BACKENDS,
    ActionExecutionConfig,
)
from pdelie.actions.interaction_rules import RULE_COUNT, RULES, InteractionRule
from pdelie.actions.parameter_action_spec import (
    PARAMETER_ACTION_FAMILIES,
    ParameterActionSpec,
    as_parameter_action_spec,
)
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
    "BENCHMARK_OUTCOMES",
    "BOUNDARY_RELATIONS",
    "BUNDLE_RULES",
    "BUNDLE_RULE_COUNT",
    "BUNDLE_RULE_IDS",
    "BUNDLE_SCHEMA_VERSION",
    "COEFFICIENT_RELATIONS",
    "COEFFICIENT_TREATMENTS",
    "COMMUTATION_REPORT_SUMMARY_TYPE",
    "COORDINATE_FIELD_ACTION_FAMILIES",
    "DERIVATIVE_NAMES",
    "DOMAIN_RELATIONS",
    "DOMAIN_TYPES",
    "EQUATION_FAMILIES",
    "EQUATION_FORMS",
    "EQUATION_RELATIONS",
    "EXPECTED_CASES",
    "EXPECTED_OPERATOR_FAMILIES",
    "INTERPOLATION_BACKENDS",
    "OBSERVED_RELATION_STATUSES",
    "PARAMETER_ACTION_FAMILIES",
    "PARAMETER_RELATIONS",
    "RULES",
    "RULE_COUNT",
    "RUNTIME_PATHS",
    "ActionExecutionConfig",
    "ActionRef",
    "BundleExecutionResult",
    "CoefficientFieldRef",
    "CoordinateFieldAction",
    "ExpectedResidualOperator",
    "ExpectedResidualRelation",
    "FittedOperatorDiagnostic",
    "InconsistentBundleError",
    "InteractionRule",
    "ParameterActionSpec",
    "ProblemActionBundle",
    "ProblemActionSpec",
    "ProblemInstanceSpec",
    "as_parameter_action_spec",
    "build_residual_commutation_report",
    "classify_runtime_path",
    "execute_bundle",
    "execute_coefficient_action",
    "execute_state_action",
    "fit_diagnostic_operator",
    "shift_cells",
    "validate_action_bundle",
    "validate_action_spec",
]
