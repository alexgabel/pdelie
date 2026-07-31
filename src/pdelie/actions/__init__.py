"""v0.36b: problem-action contracts and their legality rules. Submodule-only."""

from __future__ import annotations

from pdelie.actions.action_ref import ACTION_TARGETS, ActionRef
from pdelie.actions.interaction_rules import RULE_COUNT, RULES, InteractionRule
from pdelie.actions.problem_action_spec import (
    BOUNDARY_RELATIONS,
    DOMAIN_RELATIONS,
    EQUATION_RELATIONS,
    PARAMETER_RELATIONS,
    ProblemActionSpec,
    validate_action_spec,
)

__all__ = [
    "ACTION_TARGETS",
    "BOUNDARY_RELATIONS",
    "DOMAIN_RELATIONS",
    "EQUATION_RELATIONS",
    "PARAMETER_RELATIONS",
    "RULES",
    "RULE_COUNT",
    "ActionRef",
    "InteractionRule",
    "ProblemActionSpec",
    "validate_action_spec",
]
