"""v0.36b: what a transformation claims to do to a problem.

``ProblemActionSpec`` records **five** independent *relations* -- what the
transformation claims is preserved, transformed, or invalidated -- alongside the
*actions* that implement them. The pairing is the point: a spec that claims
parameters were transformed while naming no action that transforms them is not
describing anything, and :func:`validate_action_spec` refuses it.

The axes are deliberately independent rather than one collapsed vocabulary.
Boundary preservation is orthogonal to equation equivalence: a transformation
can be an equivalence transformation with the boundary preserved, or an
equivalence transformation with the boundary destroyed, and a single enum cannot
say which.

The vocabularies here deliberately echo distinctions the repository already
draws and has already paid for:

* ``equivalence_transformation`` versus ``same_equation`` is the v0.34b
  finding -- a translation of a variable-coefficient problem is an *equivalence*
  mapping it to a different problem unless the background travels with it, a
  distinction measured at 77x to 15437x separation in residual L2.
* ``overlap_crop`` and ``interior_only`` are the v0.33b overlap-crop
  verification and the v0.33a interior-only claim: those established that a
  finite transform on a nonperiodic domain preserves the *interior* differential
  operator, not the boundary-value problem.

``coefficient_relation`` was added after the axes were first frozen. Its absence
was a real gap: ``coefficient_field_action`` could be attached, but the claim it
implements -- whether the background is held ``fixed`` or ``co_transformed`` --
had nowhere to live, which is precisely the unpaired state this module exists to
refuse. It is the *only* place that claim belongs; a coefficient-field reference
describes the field, not the transformation currently applied to it.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from pdelie.actions.action_ref import ActionRef
from pdelie.artifact.semantic_hash import semantic_hash
from pdelie.errors import ScopeValidationError

__all__ = [
    "BOUNDARY_RELATIONS",
    "COEFFICIENT_RELATIONS",
    "DOMAIN_RELATIONS",
    "EQUATION_RELATIONS",
    "PARAMETER_RELATIONS",
    "ProblemActionSpec",
    "validate_action_spec",
]

#: What the transformation claims about the governing equation.
EQUATION_RELATIONS: tuple[str, ...] = (
    "same_equation",
    "equivalence_transformation",
    "equation_invalid",
)

#: What it claims about the equation's parameters.
PARAMETER_RELATIONS: tuple[str, ...] = ("preserved", "transformed", "unknown")

#: What it claims about a variable-coefficient background field. ``fixed`` is
#: the v0.34b non-equivalence case (the background stays put while the state
#: moves); ``co_transformed`` is the case where the background travels with the
#: transformation. ``not_applicable`` is the honest answer for a
#: constant-coefficient problem, and is distinct from ``unknown``.
COEFFICIENT_RELATIONS: tuple[str, ...] = (
    "fixed",
    "co_transformed",
    "not_applicable",
    "unknown",
)

#: What it claims about the spatial domain.
DOMAIN_RELATIONS: tuple[str, ...] = ("preserved", "overlap_crop", "not_preserved", "unknown")

#: What it claims about the boundary conditions.
BOUNDARY_RELATIONS: tuple[str, ...] = (
    "preserved",
    "interior_only",
    "not_preserved",
    "unknown",
)


@dataclass(frozen=True)
class ProblemActionSpec:
    """A transformation's claims about a problem, plus the actions implementing them."""

    action_id: str
    equation_relation: str
    parameter_relation: str
    domain_relation: str
    boundary_relation: str
    # Defaulted so existing four-axis specs keep constructing. "not_applicable"
    # is the correct default: a spec that never mentioned a coefficient field
    # was describing a problem without one.
    coefficient_relation: str = "not_applicable"
    state_action: ActionRef | None = None
    parameter_action: ActionRef | None = None
    coefficient_field_action: ActionRef | None = None
    coordinate_action: ActionRef | None = None
    domain_action: ActionRef | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.action_id, str) or not self.action_id.strip():
            raise ScopeValidationError("action_id must be a non-empty string.")
        for name, allowed in (
            ("equation_relation", EQUATION_RELATIONS),
            ("parameter_relation", PARAMETER_RELATIONS),
            ("domain_relation", DOMAIN_RELATIONS),
            ("boundary_relation", BOUNDARY_RELATIONS),
            ("coefficient_relation", COEFFICIENT_RELATIONS),
        ):
            value = getattr(self, name)
            if value not in allowed:
                raise ScopeValidationError(
                    f"{name} {value!r} is not one of {list(allowed)}."
                )
        for name in (
            "state_action",
            "parameter_action",
            "coefficient_field_action",
            "coordinate_action",
            "domain_action",
        ):
            value = getattr(self, name)
            if value is not None and not isinstance(value, ActionRef):
                raise ScopeValidationError(f"{name} must be an ActionRef or None.")
        if not isinstance(self.metadata, Mapping):
            raise ScopeValidationError("metadata must be a mapping.")
        object.__setattr__(self, "metadata", dict(self.metadata))
        semantic_hash(self.as_dict())

    def identity(self) -> str:
        return semantic_hash(self.as_dict())

    def as_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "equation_relation": self.equation_relation,
            "parameter_relation": self.parameter_relation,
            "domain_relation": self.domain_relation,
            "boundary_relation": self.boundary_relation,
            "coefficient_relation": self.coefficient_relation,
            "state_action": None if self.state_action is None else self.state_action.as_dict(),
            "parameter_action": (
                None if self.parameter_action is None else self.parameter_action.as_dict()
            ),
            "coefficient_field_action": (
                None
                if self.coefficient_field_action is None
                else self.coefficient_field_action.as_dict()
            ),
            "coordinate_action": (
                None if self.coordinate_action is None else self.coordinate_action.as_dict()
            ),
            "domain_action": (
                None if self.domain_action is None else self.domain_action.as_dict()
            ),
            "metadata": dict(self.metadata),
        }


def validate_action_spec(spec: ProblemActionSpec) -> None:
    """Refuse a spec whose claims contradict each other or its actions.

    Raises :class:`~pdelie.errors.ScopeValidationError` on the first rule that
    fires. Rules live in :mod:`pdelie.actions.interaction_rules` and their count
    is frozen by test -- a new rule requires a PR that grows the count together
    with an example that trips it.
    """
    from pdelie.actions.interaction_rules import RULES

    if not isinstance(spec, ProblemActionSpec):
        raise ScopeValidationError("validate_action_spec requires a ProblemActionSpec.")
    for predicate, message in RULES:
        if predicate(spec):
            raise ScopeValidationError(f"illegal ProblemActionSpec: {message}")
