"""v0.36b: DesignBudget."""

from __future__ import annotations

import json

import pytest

from pdelie.design import BUDGET_UNITS, DUPLICATE_POLICIES, DesignBudget
from pdelie.errors import ScopeValidationError


def budget(**overrides: object) -> DesignBudget:
    base = {
        "budget_value": 30.0,
        "budget_unit": "rows",
        "num_views": 1,
        "allocation_policy": "uniform",
        "grouping_policy": "by_trajectory",
        "duplicate_policy": "retain",
        "row_weight_policy": "unit",
        "train_only": True,
    }
    base.update(overrides)
    return DesignBudget(**base)  # type: ignore[arg-type]


def test_round_trips_through_strict_json() -> None:
    payload = budget().as_dict()
    assert json.loads(json.dumps(payload, allow_nan=False)) == payload


def test_the_seven_unit_vocabulary_is_complete() -> None:
    assert len(BUDGET_UNITS) == 7
    for unit in BUDGET_UNITS:
        assert budget(budget_unit=unit).budget_unit == unit


@pytest.mark.parametrize("policy", DUPLICATE_POLICIES)
def test_every_duplicate_policy_is_constructible(policy: str) -> None:
    assert budget(duplicate_policy=policy).duplicate_policy == policy


def test_unknown_budget_unit_raises_rather_than_being_accepted() -> None:
    """A unit silently accepted is a fairness claim silently unverified."""
    for bad in ("bytes", "ROWS", "row", ""):
        with pytest.raises(ScopeValidationError, match="budget_unit"):
            budget(budget_unit=bad)


def test_unknown_duplicate_policy_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="duplicate_policy"):
        budget(duplicate_policy="ignore")


def test_negative_budget_and_zero_views_are_refused() -> None:
    with pytest.raises(ScopeValidationError, match="non-negative"):
        budget(budget_value=-1)
    with pytest.raises(ScopeValidationError, match="at least 1"):
        budget(num_views=0)


def test_train_only_must_be_a_strict_bool() -> None:
    """Whether heldout data was in scope is a yes-or-no fact, not a truthy one."""
    for bad in (1, "yes", None):
        with pytest.raises(ScopeValidationError, match="train_only must be a bool"):
            budget(train_only=bad)


def test_budget_value_is_coerced_to_float() -> None:
    assert isinstance(budget(budget_value=30).budget_value, float)


def test_identity_separates_budgets_that_are_not_interchangeable() -> None:
    """Same number, different unit or duplicate policy: not the same budget."""
    rows = budget(budget_unit="rows")
    unique = budget(budget_unit="unique_rows")
    dedup = budget(duplicate_policy="deduplicate")
    assert len({rows.identity(), unique.identity(), dedup.identity()}) == 3


def test_row_budget_reconstructs_from_a_histogram() -> None:
    """The b-gate: sum of per-group multiplicities equals the budget in rows."""
    histogram = [("traj_a", 12), ("traj_b", 10), ("traj_c", 8)]
    spent = budget(budget_value=30.0, budget_unit="rows")
    assert sum(count for _group, count in histogram) == spent.budget_value


def test_not_exported_from_the_root_namespace() -> None:
    import pdelie

    assert "DesignBudget" not in pdelie.__all__
    assert not hasattr(pdelie, "DesignBudget")


def test_non_numeric_budget_value_is_refused() -> None:
    for bad in ("30", None, True):
        with pytest.raises(ScopeValidationError, match="budget_value"):
            budget(budget_value=bad)


def test_blank_policy_strings_are_refused() -> None:
    for field in ("allocation_policy", "grouping_policy", "row_weight_policy"):
        with pytest.raises(ScopeValidationError, match=field):
            budget(**{field: "  "})


def test_non_integer_num_views_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="num_views must be an integer"):
        budget(num_views=2.5)
