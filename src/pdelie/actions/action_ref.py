"""v0.36b: a reference to one concrete action within a transformation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from pdelie.artifact.semantic_hash import semantic_hash
from pdelie.errors import ScopeValidationError

__all__ = ["ACTION_TARGETS", "ActionRef"]

#: What an action acts on. These are the five independently-transformable parts
#: of a problem; ``ProblemActionSpec`` carries at most one action per target.
ACTION_TARGETS: tuple[str, ...] = (
    "state",
    "parameter",
    "coefficient_field",
    "coordinate",
    "domain",
)


@dataclass(frozen=True)
class ActionRef:
    """One action: what it targets, what family it belongs to, its parameters."""

    action_target: str
    action_family: str
    action_parameter_id: str
    parameters: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.action_target not in ACTION_TARGETS:
            raise ScopeValidationError(
                f"action_target {self.action_target!r} is not one of {list(ACTION_TARGETS)}."
            )
        for name in ("action_family", "action_parameter_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ScopeValidationError(f"{name} must be a non-empty string.")
        if not isinstance(self.parameters, Mapping):
            raise ScopeValidationError("parameters must be a mapping.")
        object.__setattr__(self, "parameters", dict(self.parameters))
        semantic_hash(self.as_dict())

    def identity(self) -> str:
        return semantic_hash(self.as_dict())

    def as_dict(self) -> dict[str, Any]:
        return {
            "action_target": self.action_target,
            "action_family": self.action_family,
            "action_parameter_id": self.action_parameter_id,
            "parameters": dict(self.parameters),
        }
