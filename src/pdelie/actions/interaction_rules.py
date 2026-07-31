"""v0.36b: rules that reject self-contradictory ProblemActionSpecs.

Each rule is a ``(predicate, message)`` pair. The predicate returns ``True``
when the spec is **illegal**, and the message says why in the terms the caller
used. :func:`~pdelie.actions.problem_action_spec.validate_action_spec` raises on
the first match.

The rule count is frozen by test
================================

``RULE_COUNT`` is asserted. The engine is knowingly incomplete -- these six are
the contradictions measurement has surfaced so far, not a proof of exhaustion --
so growth must be deliberate: a new rule requires a PR that raises the count and
adds an example that trips it. Without that, rules accumulate silently and
nobody can tell whether the engine got stricter or a spec got sloppier.
"""

from __future__ import annotations

from collections.abc import Callable

from pdelie.actions.problem_action_spec import ProblemActionSpec

__all__ = ["RULES", "RULE_COUNT", "InteractionRule"]

InteractionRule = tuple[Callable[[ProblemActionSpec], bool], str]

RULES: tuple[InteractionRule, ...] = (
    (
        lambda s: s.equation_relation == "same_equation"
        and s.parameter_relation == "transformed"
        and s.parameter_action is None
        and s.coefficient_field_action is None,
        (
            "same_equation with transformed parameters requires a parameter or "
            "coefficient_field action"
        ),
    ),
    (
        lambda s: s.equation_relation == "equivalence_transformation"
        and s.parameter_action is None
        and s.coefficient_field_action is None
        and s.coordinate_action is None
        and s.domain_action is None,
        "equivalence_transformation requires at least one non-state action",
    ),
    (
        lambda s: s.equation_relation == "equation_invalid"
        and s.domain_relation in ("preserved", "overlap_crop"),
        "equation_invalid cannot claim a preserved or overlap-crop domain",
    ),
    (
        lambda s: s.domain_relation == "overlap_crop"
        and s.boundary_relation not in ("interior_only", "unknown"),
        "overlap_crop requires boundary_relation in {interior_only, unknown}",
    ),
    (
        lambda s: s.parameter_relation == "transformed"
        and s.parameter_action is None
        and s.coefficient_field_action is None,
        (
            "transformed parameter requires a non-null parameter or "
            "coefficient_field action"
        ),
    ),
    (
        lambda s: s.domain_relation == "preserved"
        and s.boundary_relation == "not_preserved",
        "domain preserved with boundary not preserved is contradictory",
    ),
)

#: Frozen by test. Raising this is a deliberate act, not a side effect.
RULE_COUNT = len(RULES)
