"""v0.36b: ActionRef and ProblemActionSpec shape."""

from __future__ import annotations

import json

import pytest

from pdelie.actions import (
    ACTION_TARGETS,
    BOUNDARY_RELATIONS,
    DOMAIN_RELATIONS,
    EQUATION_RELATIONS,
    PARAMETER_RELATIONS,
    ActionRef,
    ProblemActionSpec,
)
from pdelie.errors import ScopeValidationError


def action(target: str = "state") -> ActionRef:
    return ActionRef(
        action_target=target, action_family="translation", action_parameter_id="eps=1.0"
    )


def spec(**overrides: object) -> ProblemActionSpec:
    base = {
        "action_id": "translate_x",
        "equation_relation": "same_equation",
        "parameter_relation": "preserved",
        "domain_relation": "preserved",
        "boundary_relation": "preserved",
        "state_action": action(),
    }
    base.update(overrides)
    return ProblemActionSpec(**base)  # type: ignore[arg-type]


def test_round_trips_through_strict_json() -> None:
    payload = spec().as_dict()
    assert json.loads(json.dumps(payload, allow_nan=False)) == payload


@pytest.mark.parametrize("target", ACTION_TARGETS)
def test_every_action_target_is_constructible(target: str) -> None:
    assert action(target).action_target == target


def test_unknown_action_target_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="action_target"):
        ActionRef(action_target="vibes", action_family="f", action_parameter_id="p")


@pytest.mark.parametrize(
    "field,allowed",
    [
        ("equation_relation", EQUATION_RELATIONS),
        ("parameter_relation", PARAMETER_RELATIONS),
        ("domain_relation", DOMAIN_RELATIONS),
        ("boundary_relation", BOUNDARY_RELATIONS),
    ],
)
def test_every_relation_vocabulary_is_closed(field: str, allowed: tuple[str, ...]) -> None:
    with pytest.raises(ScopeValidationError, match=field):
        spec(**{field: "not_in_the_vocabulary"})
    assert len(allowed) >= 3


def test_the_vocabularies_echo_shipped_distinctions() -> None:
    """These are not new inventions; they name distinctions already paid for."""
    assert "equivalence_transformation" in EQUATION_RELATIONS  # v0.34b
    assert "overlap_crop" in DOMAIN_RELATIONS  # v0.33b
    assert "interior_only" in BOUNDARY_RELATIONS  # v0.33a


def test_non_action_ref_in_an_action_slot_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="must be an ActionRef or None"):
        spec(parameter_action="a string")


def test_identity_distinguishes_different_claims() -> None:
    assert spec().identity() != spec(boundary_relation="unknown").identity()


def test_not_exported_from_the_root_namespace() -> None:
    import pdelie

    for name in ("ActionRef", "ProblemActionSpec", "validate_action_spec"):
        assert name not in pdelie.__all__
        assert not hasattr(pdelie, name)


def test_blank_action_family_or_parameter_id_is_refused() -> None:
    for field in ("action_family", "action_parameter_id"):
        kwargs = {"action_target": "state", "action_family": "f", "action_parameter_id": "p"}
        kwargs[field] = "   "
        with pytest.raises(ScopeValidationError, match=field):
            ActionRef(**kwargs)  # type: ignore[arg-type]


def test_non_mapping_parameters_and_metadata_are_refused() -> None:
    with pytest.raises(ScopeValidationError, match="parameters must be a mapping"):
        ActionRef(
            action_target="state", action_family="f", action_parameter_id="p", parameters=["a"]
        )  # type: ignore[arg-type]
    with pytest.raises(ScopeValidationError, match="metadata must be a mapping"):
        spec(metadata=["not", "a", "mapping"])


def test_blank_action_id_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="action_id"):
        spec(action_id="   ")


def test_non_strict_json_parameters_are_refused() -> None:
    with pytest.raises(ValueError):
        ActionRef(
            action_target="state",
            action_family="f",
            action_parameter_id="p",
            parameters={"eps": float("inf")},
        )
