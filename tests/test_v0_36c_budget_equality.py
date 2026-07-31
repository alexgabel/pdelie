"""v0.36c: budget-incomparable pair handling."""

from __future__ import annotations

import pytest

from pdelie.design import DesignBudget, budgets_are_equal
from pdelie.errors import ScopeValidationError

BASE = {
    "budget_value": 30.0, "budget_unit": "rows", "num_views": 1,
    "allocation_policy": "uniform", "grouping_policy": "by_trajectory",
    "duplicate_policy": "retain", "row_weight_policy": "unit", "train_only": True,
}


def budget(**overrides) -> DesignBudget:
    return DesignBudget(**{**BASE, **overrides})


def test_identical_budgets_are_equal() -> None:
    equal, differing = budgets_are_equal(budget(), budget())
    assert equal is True
    assert differing == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("budget_value", 31.0),
        ("budget_unit", "unique_rows"),
        ("num_views", 2),
        ("allocation_policy", "proportional"),
        ("grouping_policy", "by_time"),
        ("duplicate_policy", "deduplicate"),
        ("row_weight_policy", "inverse_variance"),
        ("train_only", False),
    ],
)
def test_every_budget_field_can_make_two_designs_incomparable(field: str, value) -> None:
    """All eight fields participate. A budget differing in any one is a
    different allowance, and a delta across it measures the budget too."""
    equal, differing = budgets_are_equal(budget(), budget(**{field: value}))
    assert equal is False
    assert differing == [field]


def test_the_same_number_in_a_different_unit_is_not_the_same_budget() -> None:
    """30 rows and 30 unique rows are different allowances."""
    equal, differing = budgets_are_equal(
        budget(budget_unit="rows"), budget(budget_unit="unique_rows")
    )
    assert equal is False
    assert differing == ["budget_unit"]


def test_the_same_number_under_a_different_duplicate_policy_differs() -> None:
    equal, _ = budgets_are_equal(
        budget(duplicate_policy="retain"), budget(duplicate_policy="deduplicate")
    )
    assert equal is False


def test_multiple_differences_are_all_reported() -> None:
    equal, differing = budgets_are_equal(
        budget(), budget(budget_value=10.0, budget_unit="views", num_views=3)
    )
    assert equal is False
    assert set(differing) == {"budget_value", "budget_unit", "num_views"}


def test_non_budget_arguments_are_refused() -> None:
    with pytest.raises(ScopeValidationError, match="DesignBudget"):
        budgets_are_equal(budget(), {"budget_value": 30.0})
