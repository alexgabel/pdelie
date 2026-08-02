"""v0.38: a parameter action names what it acts on, as a declared field.

Why this type exists
====================

v0.38e made ``target_parameters`` reachable as a key inside an ``ActionRef``'s
free-form ``parameters`` mapping. That closed the defect -- the executor stopped
rescaling every numeric parameter -- but it left the target as a *magic key*:
not typed, not validated at construction, and discoverable only by reading the
consistency module.

A magic key in a free-form mapping is how the original defect happened. The
target is now a declared field with its own validation.

``target_parameters=None`` is retained deliberately
===================================================

It means "no target declared", which is a real and distinct state from
``()`` ("declared, and empty" -- refused) and from naming one. On a
single-parameter problem an undeclared target is unambiguous by exhaustion; on a
multi-parameter problem it is refused. Both need to be expressible, and benchmark
case C-8 exists precisely to exercise the second.

Validation lives in two places, for a reason
============================================

Shape is checked here: duplicates, emptiness, bare strings, non-strings. Whether
a named target *exists* cannot be checked here -- it needs the problem instance
-- so it is checked when the bundle is assembled, where both are present.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from pdelie.actions.action_ref import ActionRef
from pdelie.artifact.semantic_hash import semantic_hash
from pdelie.errors import ScopeValidationError

__all__ = [
    "PARAMETER_ACTION_FAMILIES",
    "ParameterActionSpec",
    "as_parameter_action_spec",
]

#: Families a parameter action may declare. Growth is by adding a family, not by
#: widening an existing one's parameter mapping.
PARAMETER_ACTION_FAMILIES: tuple[str, ...] = ("scalar_rescale", "identity")


@dataclass(frozen=True)
class ParameterActionSpec:
    """A parameter action, with its targets declared rather than implied."""

    action_family: str
    action_parameter_id: str
    #: ``None`` means no target was declared. ``()`` is refused -- an action
    #: targeting nothing is not an action, and the two must not be conflated.
    #:
    #: Declared wider than it is stored, matching
    #: :attr:`CoefficientFieldRef.coordinate_dependency`. A caller really can
    #: pass a bare string, and the guard against that is only reachable if the
    #: type admits it -- narrowing the annotation to ``tuple[str, ...]`` made
    #: mypy call the guard dead code while runtime callers still tripped it.
    #: After ``__post_init__`` it is always ``tuple[str, ...] | None``.
    target_parameters: Sequence[str] | str | None = None
    parameters: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.action_family not in PARAMETER_ACTION_FAMILIES:
            raise ScopeValidationError(
                f"action_family {self.action_family!r} is not one of "
                f"{list(PARAMETER_ACTION_FAMILIES)}."
            )
        if not isinstance(self.action_parameter_id, str) or not self.action_parameter_id.strip():
            raise ScopeValidationError("action_parameter_id must be a non-empty string.")
        if not isinstance(self.parameters, Mapping):
            raise ScopeValidationError("parameters must be a mapping.")
        object.__setattr__(self, "parameters", dict(self.parameters))

        targets = self.target_parameters
        if targets is None:
            semantic_hash(self.as_dict())
            return

        if isinstance(targets, (str, bytes)) or not isinstance(targets, Sequence):
            raise ScopeValidationError(
                f"target_parameters must be a sequence of names, not "
                f"{type(targets).__name__}. A bare string would iterate as "
                f"characters and silently target nothing that exists."
            )
        names = tuple(str(name) for name in targets)
        if not names:
            raise ScopeValidationError(
                "target_parameters is empty. An action targeting nothing is not "
                "an action; pass None if there is no target to name, which is a "
                "different statement."
            )
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            raise ScopeValidationError(
                f"target_parameters repeats {duplicates}. A repeated target reads "
                f"as an intention to apply the action twice, which is not what "
                f"any family here means."
            )
        # Sorted so two specs naming the same targets in different orders are the
        # same spec, and hash identically. Order carries no meaning for a set of
        # targets, and letting it change the hash would make identity depend on
        # how a caller happened to type the list.
        object.__setattr__(self, "target_parameters", tuple(sorted(names)))
        semantic_hash(self.as_dict())

    @property
    def resolved_targets(self) -> tuple[str, ...] | None:
        """The targets in their stored form: sorted, deduplicated, or ``None``.

        ``target_parameters`` is annotated wide because a caller can pass a
        bare string and the guard against that must be reachable. After
        ``__post_init__`` it is always a tuple or ``None``, and this is the
        accessor that says so -- so readers narrow once here instead of at
        every call site.
        """
        targets = self.target_parameters
        if targets is None:
            return None
        assert isinstance(targets, tuple)
        return targets

    @property
    def declares_a_target(self) -> bool:
        return self.target_parameters is not None

    def identity(self) -> str:
        return semantic_hash(self.as_dict())

    def as_dict(self) -> dict[str, Any]:
        return {
            "action_target": "parameter",
            "action_family": self.action_family,
            "action_parameter_id": self.action_parameter_id,
            "target_parameters": (
                None if self.target_parameters is None else list(self.target_parameters)
            ),
            "parameters": dict(self.parameters),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ParameterActionSpec:
        """Round-trip counterpart to :meth:`as_dict`."""
        if not isinstance(payload, Mapping):
            raise ScopeValidationError("from_dict requires a mapping.")
        targets = payload.get("target_parameters")
        return cls(
            action_family=str(payload["action_family"]),
            action_parameter_id=str(payload["action_parameter_id"]),
            target_parameters=None if targets is None else tuple(targets),
            parameters=dict(payload.get("parameters") or {}),
        )


def as_parameter_action_spec(action: object) -> ParameterActionSpec:
    """Normalise a parameter action to the typed form.

    An :class:`~pdelie.actions.action_ref.ActionRef` carrying a
    ``target_parameters`` key is accepted and upgraded, so v0.38e call sites keep
    working. The *stored* value is always the typed one, so exactly one
    representation reaches anything downstream -- accepting two shapes and
    keeping both is how a mapping comes to have two answers for one question.
    """
    if isinstance(action, ParameterActionSpec):
        return action
    if not isinstance(action, ActionRef):
        raise ScopeValidationError(
            f"a parameter action must be a ParameterActionSpec or an ActionRef, "
            f"not {type(action).__name__}."
        )
    if action.action_target != "parameter":
        raise ScopeValidationError(
            f"action_target {action.action_target!r} cannot be used as a "
            f"parameter action."
        )
    remaining = {k: v for k, v in action.parameters.items() if k != "target_parameters"}
    # Passed through UNCONVERTED. An earlier version wrote `tuple(raw)` here,
    # which turned a bare string "nu" into ('n', 'u') before ParameterActionSpec
    # could see it was a string -- so the guard against exactly that never fired,
    # and the failure surfaced later as "targets ['n','u'] are not parameters".
    # A normaliser that pre-converts its input destroys the evidence the
    # validator exists to read.
    return ParameterActionSpec(
        action_family=action.action_family,
        action_parameter_id=action.action_parameter_id,
        target_parameters=action.parameters.get("target_parameters"),
        parameters=remaining,
    )
