"""v0.36b: the interaction rule engine.

One failing example per rule, and twenty legal specs that must pass untouched.
The rule count is frozen so growth is deliberate.
"""

from __future__ import annotations

import itertools

import pytest

from pdelie.actions import (
    RULE_COUNT,
    RULES,
    ActionRef,
    ProblemActionSpec,
    validate_action_spec,
)
from pdelie.errors import ScopeValidationError


def act(target: str) -> ActionRef:
    return ActionRef(action_target=target, action_family="f", action_parameter_id="p")


def build(**overrides: object) -> ProblemActionSpec:
    base = {
        "action_id": "a",
        "equation_relation": "same_equation",
        "parameter_relation": "preserved",
        "domain_relation": "preserved",
        "boundary_relation": "preserved",
    }
    base.update(overrides)
    return ProblemActionSpec(**base)  # type: ignore[arg-type]


#: One spec per rule, each tripping exactly the rule it is paired with.
FAILING_EXAMPLES: tuple[tuple[str, ProblemActionSpec], ...] = (
    (
        "same_equation with transformed parameters",
        build(equation_relation="same_equation", parameter_relation="transformed"),
    ),
    (
        "equivalence_transformation requires at least one non-state",
        build(equation_relation="equivalence_transformation", state_action=act("state")),
    ),
    (
        "equation_invalid cannot claim a preserved",
        build(equation_relation="equation_invalid", domain_relation="preserved"),
    ),
    (
        "overlap_crop requires boundary_relation",
        build(domain_relation="overlap_crop", boundary_relation="preserved"),
    ),
    (
        "transformed parameter requires a non-null",
        build(
            equation_relation="equivalence_transformation",
            parameter_relation="transformed",
            coordinate_action=act("coordinate"),
        ),
    ),
    (
        "domain preserved with boundary not preserved",
        build(domain_relation="preserved", boundary_relation="not_preserved"),
    ),
)


def test_rule_count_is_frozen() -> None:
    """Growth must be deliberate: a new rule needs a PR that raises this number."""
    assert RULE_COUNT == 6
    assert len(RULES) == RULE_COUNT


@pytest.mark.parametrize("expected_message,spec", FAILING_EXAMPLES, ids=lambda v: str(v)[:40])
def test_each_rule_rejects_its_canonical_example(
    expected_message: str, spec: ProblemActionSpec
) -> None:
    with pytest.raises(ScopeValidationError, match="illegal ProblemActionSpec"):
        validate_action_spec(spec)
    with pytest.raises(ScopeValidationError) as excinfo:
        validate_action_spec(spec)
    assert expected_message in str(excinfo.value)


def test_every_rule_is_reachable_by_some_example() -> None:
    """A rule no example trips is a rule nobody has tested."""
    tripped: set[int] = set()
    for _message, spec in FAILING_EXAMPLES:
        for index, (predicate, _text) in enumerate(RULES):
            if predicate(spec):
                tripped.add(index)
                break
    assert tripped == set(range(RULE_COUNT))


def legal_specs() -> list[ProblemActionSpec]:
    """Twenty canonical specs that must all validate."""
    specs = [
        build(state_action=act("state")),
        build(boundary_relation="unknown"),
        build(domain_relation="unknown", boundary_relation="unknown"),
        build(parameter_relation="unknown"),
        build(domain_relation="overlap_crop", boundary_relation="interior_only"),
        build(domain_relation="overlap_crop", boundary_relation="unknown"),
        build(domain_relation="not_preserved", boundary_relation="not_preserved"),
        build(
            equation_relation="same_equation",
            parameter_relation="transformed",
            parameter_action=act("parameter"),
        ),
        build(
            equation_relation="same_equation",
            parameter_relation="transformed",
            coefficient_field_action=act("coefficient_field"),
        ),
        build(
            equation_relation="equivalence_transformation",
            coefficient_field_action=act("coefficient_field"),
        ),
        build(equation_relation="equivalence_transformation", coordinate_action=act("coordinate")),
        build(equation_relation="equivalence_transformation", domain_action=act("domain")),
        build(
            equation_relation="equivalence_transformation",
            parameter_relation="transformed",
            parameter_action=act("parameter"),
        ),
        build(equation_relation="equation_invalid", domain_relation="not_preserved"),
        build(equation_relation="equation_invalid", domain_relation="unknown"),
        build(
            equation_relation="equation_invalid",
            domain_relation="not_preserved",
            boundary_relation="not_preserved",
        ),
        build(state_action=act("state"), coordinate_action=act("coordinate")),
        build(boundary_relation="interior_only"),
        build(domain_relation="unknown", boundary_relation="interior_only"),
        build(
            equation_relation="equivalence_transformation",
            parameter_relation="unknown",
            domain_action=act("domain"),
            state_action=act("state"),
        ),
    ]
    assert len(specs) == 20
    return specs


@pytest.mark.parametrize("spec", legal_specs(), ids=lambda s: s.identity()[:12])
def test_canonical_legal_specs_pass(spec: ProblemActionSpec) -> None:
    validate_action_spec(spec)


def test_validate_refuses_a_non_spec() -> None:
    with pytest.raises(ScopeValidationError, match="requires a ProblemActionSpec"):
        validate_action_spec({"equation_relation": "same_equation"})  # type: ignore[arg-type]


def test_no_legal_spec_trips_any_rule() -> None:
    """Belt and braces: the engine must not be quietly rejecting valid combinations."""
    for spec in legal_specs():
        assert not any(predicate(spec) for predicate, _ in RULES)


def test_the_engine_is_documented_as_incomplete() -> None:
    """Honest scope: six contradictions found so far, not a proof of exhaustion."""
    from pdelie.actions import interaction_rules

    assert "incomplete" in (interaction_rules.__doc__ or "").lower()


def test_rules_do_not_reject_every_combination() -> None:
    """A rule set that rejects everything would pass the failing tests vacuously."""
    accepted = 0
    for equation, parameter in itertools.product(
        ("same_equation", "equivalence_transformation"), ("preserved", "unknown")
    ):
        spec = build(
            equation_relation=equation,
            parameter_relation=parameter,
            coordinate_action=act("coordinate"),
        )
        if not any(predicate(spec) for predicate, _ in RULES):
            accepted += 1
    assert accepted >= 3
