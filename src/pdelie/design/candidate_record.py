"""v0.36c: one design candidate, and what it was allowed to know.

A comparison between two designs is only meaningful if both declare what
information they had access to. A method that peeks at the true support will
beat one that does not, and reporting that as a win is not a finding -- it is a
category error.

So :class:`DesignCandidateRecord` requires **all six** access flags. A missing
flag raises rather than defaulting to ``False``, because "we did not think about
it" and "we do not use it" are different claims and only one of them is
evidence.

Qualification, not "oracle"
==========================

Every candidate declares a :data:`METHOD_CLASSES` value. The bare word "oracle"
is not one of them, and is asserted absent from emitted payloads: it collapses
four genuinely different situations into one dismissive label. A method that
enumerates every subset of a small problem is *exact*, not privileged. A method
that reads the full design matrix is using information a practitioner has. A
method that reads the true support is using information nobody has. Those need
different names because they support different conclusions.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from pdelie.artifact.semantic_hash import semantic_hash
from pdelie.design.budget import DesignBudget
from pdelie.errors import ScopeValidationError

__all__ = [
    "MANDATORY_ACCESS_KEYS",
    "METHOD_CLASSES",
    "DesignCandidateRecord",
    "validate_information_access",
]

#: Every flag a candidate must declare. All six are mandatory.
MANDATORY_ACCESS_KEYS: frozenset[str] = frozenset(
    {
        "uses_true_support",
        "uses_true_coefficients",
        "requires_full_domain",
        "requires_unobserved_rows",
        "requires_heldout_data",
        "uses_future_time",
    }
)

#: What kind of thing a candidate is. Replaces the bare word "oracle".
METHOD_CLASSES: tuple[str, ...] = (
    "attainable_policy",
    "full_design_matrix_heuristic",
    "true_support_diagnostic_oracle",
    "exact_small_problem_solver",
)

#: Classes that use information a practitioner does not have at design time.
#: Reported so a reader can filter, not to disqualify: a diagnostic oracle is
#: the right tool for measuring how much a heuristic gives up.
_PRIVILEGED_CLASSES: frozenset[str] = frozenset({"true_support_diagnostic_oracle"})


def validate_information_access(access: Mapping[str, bool]) -> dict[str, bool]:
    """Require all six flags, as booleans.

    Raises on a missing key rather than defaulting it. A comparator with any
    undeclared privileged access is invalid, and silence is not a declaration.
    """
    if not isinstance(access, Mapping):
        raise ScopeValidationError("information_access must be a mapping.")
    missing = MANDATORY_ACCESS_KEYS - set(access)
    if missing:
        raise ScopeValidationError(
            f"DesignCandidateRecord.information_access is missing required keys: "
            f"{sorted(missing)}. All six flags are mandatory; a comparator with "
            f"any hidden privileged access is invalid."
        )
    unknown = set(access) - MANDATORY_ACCESS_KEYS
    if unknown:
        raise ScopeValidationError(
            f"information_access carries unknown keys {sorted(unknown)}; the six "
            f"flags are a closed vocabulary so two records can be compared."
        )
    for key, value in access.items():
        if not isinstance(value, bool):
            raise ScopeValidationError(
                f"information_access[{key!r}] must be a bool; got "
                f"{type(value).__name__}. A truthy value is not a declaration."
            )
    return dict(access)


@dataclass(frozen=True)
class DesignCandidateRecord:
    """One design produced by one method, with its budget and access declared."""

    design_id: str
    method_name: str
    method_class: str
    selected_row_indices: tuple[int, ...] | Sequence[int]
    budget: DesignBudget
    information_access: Mapping[str, bool]
    selected_condition_number: float | None = None
    seed: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("design_id", "method_name"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ScopeValidationError(f"{name} must be a non-empty string.")
        if self.method_class not in METHOD_CLASSES:
            raise ScopeValidationError(
                f"method_class {self.method_class!r} is not one of "
                f"{list(METHOD_CLASSES)}. The bare word 'oracle' is deliberately "
                f"not a class: it collapses four different situations into one."
            )
        if not isinstance(self.budget, DesignBudget):
            raise ScopeValidationError("budget must be a DesignBudget.")
        rows: object = self.selected_row_indices
        if isinstance(rows, (str, bytes)) or not isinstance(rows, Sequence):
            raise ScopeValidationError("selected_row_indices must be a sequence.")
        indices = tuple(int(value) for value in rows)
        if len(set(indices)) != len(indices):
            raise ScopeValidationError("selected_row_indices must not repeat.")
        object.__setattr__(self, "selected_row_indices", indices)
        object.__setattr__(
            self, "information_access", validate_information_access(self.information_access)
        )
        if self.selected_condition_number is not None:
            if isinstance(self.selected_condition_number, bool) or not isinstance(
                self.selected_condition_number, (int, float)
            ):
                raise ScopeValidationError(
                    "selected_condition_number must be a real number or None."
                )
            object.__setattr__(
                self, "selected_condition_number", float(self.selected_condition_number)
            )
        if self.seed is not None and (
            isinstance(self.seed, bool) or not isinstance(self.seed, int)
        ):
            raise ScopeValidationError("seed must be an int or None.")
        if not isinstance(self.metadata, Mapping):
            raise ScopeValidationError("metadata must be a mapping.")
        object.__setattr__(self, "metadata", dict(self.metadata))
        semantic_hash(self.as_dict())

    @property
    def uses_privileged_information(self) -> bool:
        """True when this candidate knows something a practitioner would not."""
        return self.method_class in _PRIVILEGED_CLASSES or any(
            self.information_access[key]
            for key in ("uses_true_support", "uses_true_coefficients", "uses_future_time")
        )

    def identity(self) -> str:
        return semantic_hash(self.as_dict())

    def as_dict(self) -> dict[str, Any]:
        return {
            "design_id": self.design_id,
            "method_name": self.method_name,
            "method_class": self.method_class,
            "selected_row_indices": list(self.selected_row_indices),
            "num_rows_selected": len(tuple(self.selected_row_indices)),
            "budget": self.budget.as_dict(),
            "information_access": dict(self.information_access),
            "uses_privileged_information": self.uses_privileged_information,
            "selected_condition_number": self.selected_condition_number,
            "seed": self.seed,
            "metadata": dict(self.metadata),
        }
