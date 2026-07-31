"""v0.36b: what "same budget" means when comparing two designs.

Two designs are only comparable if they were allowed the same resources, and
"the same resources" is ambiguous until the *unit* is named. Thirty rows drawn
from one trajectory and thirty drawn from ten are not the same design budget,
and neither is thirty rows with duplicates retained versus deduplicated.

``budget_unit`` is a closed vocabulary and an unknown string **raises**. A unit
silently accepted is a fairness claim silently unverified -- v0.36c's
budget-incomparable handling depends on this being strict.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pdelie.artifact.semantic_hash import semantic_hash
from pdelie.errors import ScopeValidationError

__all__ = ["BUDGET_UNITS", "DUPLICATE_POLICIES", "DesignBudget"]

#: The seven units a budget may be counted in.
BUDGET_UNITS: tuple[str, ...] = (
    "rows",
    "unique_rows",
    "views",
    "sensors",
    "weak_test_functions",
    "quadrature_points",
    "weighted_cost",
)

#: What happens to repeated rows. ``inverse_multiplicity`` down-weights a row by
#: how often it appears rather than dropping it.
DUPLICATE_POLICIES: tuple[str, ...] = ("retain", "deduplicate", "inverse_multiplicity")


@dataclass(frozen=True)
class DesignBudget:
    """The resource allowance a design was built under."""

    budget_value: float
    budget_unit: str
    num_views: int
    allocation_policy: str
    grouping_policy: str
    duplicate_policy: str
    row_weight_policy: str
    train_only: bool

    def __post_init__(self) -> None:
        if isinstance(self.budget_value, bool) or not isinstance(
            self.budget_value, (int, float)
        ):
            raise ScopeValidationError("budget_value must be a real number.")
        if self.budget_value < 0:
            raise ScopeValidationError("budget_value must be non-negative.")
        object.__setattr__(self, "budget_value", float(self.budget_value))

        if self.budget_unit not in BUDGET_UNITS:
            raise ScopeValidationError(
                f"budget_unit {self.budget_unit!r} is not one of {list(BUDGET_UNITS)}. "
                f"An unrecognized unit is refused rather than accepted, because a "
                f"budget whose unit is unknown cannot establish that two designs "
                f"were compared fairly."
            )
        if self.duplicate_policy not in DUPLICATE_POLICIES:
            raise ScopeValidationError(
                f"duplicate_policy {self.duplicate_policy!r} is not one of "
                f"{list(DUPLICATE_POLICIES)}."
            )
        if isinstance(self.num_views, bool) or not isinstance(self.num_views, int):
            raise ScopeValidationError("num_views must be an integer.")
        if self.num_views < 1:
            raise ScopeValidationError("num_views must be at least 1.")
        for name in ("allocation_policy", "grouping_policy", "row_weight_policy"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ScopeValidationError(f"{name} must be a non-empty string.")
        if not isinstance(self.train_only, bool):
            raise ScopeValidationError(
                "train_only must be a bool. A truthy value is not a declaration; "
                "whether heldout data was in scope is a yes-or-no fact."
            )

    def identity(self) -> str:
        return semantic_hash(self.as_dict())

    def as_dict(self) -> dict[str, Any]:
        return {
            "budget_value": self.budget_value,
            "budget_unit": self.budget_unit,
            "num_views": self.num_views,
            "allocation_policy": self.allocation_policy,
            "grouping_policy": self.grouping_policy,
            "duplicate_policy": self.duplicate_policy,
            "row_weight_policy": self.row_weight_policy,
            "train_only": self.train_only,
        }
