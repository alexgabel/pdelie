"""v0.36c: the eight design comparators."""

from __future__ import annotations

import json
import re

import numpy as np
import pytest

from pdelie.design import (
    COMPARATOR_NAMES,
    EXACT_ENUMERATION_MAX_ROWS,
    METHOD_CLASSES,
    DesignBudget,
    DesignCandidateRecord,
    d_optimal_exchange_comparator,
    exact_enumeration_comparator,
    full_field_design,
    leverage_score_selection_comparator,
    qr_pivot_selection_comparator,
    random_budget_matched_design,
    raw_local_design,
    translation_orbit_design,
)
from pdelie.errors import ScopeValidationError, ShapeValidationError


def budget(**overrides) -> DesignBudget:
    base = {
        "budget_value": 5.0, "budget_unit": "rows", "num_views": 1,
        "allocation_policy": "uniform", "grouping_policy": "by_trajectory",
        "duplicate_policy": "retain", "row_weight_policy": "unit", "train_only": True,
    }
    base.update(overrides)
    return DesignBudget(**base)


def matrix(n: int = 12, k: int = 4) -> np.ndarray:
    return np.random.default_rng(20360).standard_normal((n, k))


def every_comparator(m: np.ndarray, count: int = 5) -> list[DesignCandidateRecord]:
    b = budget()
    records = [
        raw_local_design(m, count, budget=b),
        random_budget_matched_design(m, count, budget=b, seed=1),
        translation_orbit_design(m, count, budget=b, shifts=[0, 3, 6]),
        leverage_score_selection_comparator(m, count, budget=b),
        qr_pivot_selection_comparator(m, count, budget=b),
        d_optimal_exchange_comparator(m, count, budget=b),
        full_field_design(m, budget=b),
        exact_enumeration_comparator(m, count, budget=b),
    ]
    return [r for r in records if r is not None]


def test_all_eight_comparators_are_named() -> None:
    assert len(COMPARATOR_NAMES) == 8


def test_every_comparator_produces_a_valid_record() -> None:
    records = every_comparator(matrix())
    assert len(records) == 8
    for record in records:
        assert isinstance(record, DesignCandidateRecord)
        assert record.method_class in METHOD_CLASSES
        assert len(record.information_access) == 6


def test_selected_rows_are_sorted_distinct_and_in_range() -> None:
    m = matrix()
    for record in every_comparator(m):
        rows = record.selected_row_indices
        assert list(rows) == sorted(rows)
        assert len(set(rows)) == len(rows)
        assert all(0 <= index < m.shape[0] for index in rows)


def test_budget_matched_comparators_select_the_requested_count() -> None:
    m = matrix()
    for record in every_comparator(m):
        if record.method_name == "full_field_design":
            assert len(record.selected_row_indices) == m.shape[0]
        else:
            assert len(record.selected_row_indices) == 5


# --- the three that wrap v0.35c ---------------------------------------------


@pytest.mark.parametrize(
    "comparator,wrapped",
    [
        (qr_pivot_selection_comparator, "qr_pivot_row_selection"),
        (leverage_score_selection_comparator, "leverage_row_selection"),
        (d_optimal_exchange_comparator, "d_optimal_exchange_row_selection"),
    ],
)
def test_wrapping_comparators_delegate_rather_than_reimplement(comparator, wrapped) -> None:
    """Reimplementing would fork the tie-break policy and the LINPACK safeguard,
    the latter measured load-bearing on 8 of 12 adversarial matrices."""
    record = comparator(matrix(), 5, budget=budget())
    assert record.metadata["wraps"].endswith(wrapped)


def test_wrapped_selections_match_the_v0_35c_functions_exactly() -> None:
    from pdelie.design.row_selection import (
        d_optimal_exchange_row_selection,
        leverage_row_selection,
        qr_pivot_row_selection,
    )

    m = matrix()
    pairs = [
        (qr_pivot_selection_comparator(m, 5, budget=budget()), qr_pivot_row_selection(m, 5)),
        (leverage_score_selection_comparator(m, 5, budget=budget()), leverage_row_selection(m, 5)),
        (d_optimal_exchange_comparator(m, 5, budget=budget()), d_optimal_exchange_row_selection(m, 5)),
    ]
    for record, report in pairs:
        assert list(record.selected_row_indices) == report["selected_row_indices"]


def test_leverage_declares_it_does_not_target_conditioning() -> None:
    """Measured in v0.35c: beat 8% of 40 random draws, against 100% for the others."""
    record = leverage_score_selection_comparator(matrix(), 5, budget=budget())
    assert record.metadata["targets_conditioning"] is False
    assert record.metadata["measured_v0_35c_random_draws_beaten_percent"] == 8
    assert record.information_access["requires_unobserved_rows"] is True


def test_d_optimal_records_its_start_because_the_result_depends_on_it() -> None:
    """Measured in v0.35c: 4-5 distinct optima across five random starts."""
    record = d_optimal_exchange_comparator(matrix(), 5, budget=budget())
    assert record.metadata["is_local_search"] is True
    assert record.metadata["initial_rows_source"] == "qr_pivot"
    assert "initial_row_indices" in record.metadata


def test_d_optimal_with_a_seed_uses_a_seeded_start_and_reproduces() -> None:
    m = matrix(20, 4)
    first = d_optimal_exchange_comparator(m, 5, budget=budget(), seed=7)
    second = d_optimal_exchange_comparator(m, 5, budget=budget(), seed=7)
    assert first.selected_row_indices == second.selected_row_indices
    assert first.metadata["initial_rows_source"] == "caller_supplied"
    assert first.seed == 7


# --- access declarations ----------------------------------------------------


def test_full_field_declares_it_requires_the_whole_domain() -> None:
    record = full_field_design(matrix(), budget=budget())
    assert record.information_access["requires_full_domain"] is True


def test_attainable_policies_declare_no_privileged_access() -> None:
    """The three a practitioner could actually run."""
    b = budget()
    m = matrix()
    for record in (
        raw_local_design(m, 5, budget=b),
        random_budget_matched_design(m, 5, budget=b, seed=1),
        translation_orbit_design(m, 5, budget=b, shifts=[0, 3, 6]),
    ):
        assert record.method_class == "attainable_policy"
        assert record.uses_privileged_information is False
        assert not any(record.information_access.values())


def test_no_comparator_declares_true_support_access() -> None:
    """None of the eight peeks at the answer; the taxonomy reserves that class."""
    for record in every_comparator(matrix()):
        assert record.information_access["uses_true_support"] is False
        assert record.information_access["uses_true_coefficients"] is False


# --- exact enumeration ------------------------------------------------------


def test_exact_enumeration_returns_none_above_the_row_cap() -> None:
    assert EXACT_ENUMERATION_MAX_ROWS == 20
    big = np.random.default_rng(1).standard_normal((25, 4))
    assert exact_enumeration_comparator(big, 5, budget=budget()) is None


def test_exact_enumeration_is_optimal_within_its_reach() -> None:
    """It finds the genuine minimum, so nothing else can beat it."""
    import itertools

    m = matrix(10, 3)
    record = exact_enumeration_comparator(m, 4, budget=budget())
    assert record is not None
    best = min(
        np.linalg.cond(m[list(c)]) for c in itertools.combinations(range(10), 4)
    )
    assert record.selected_condition_number == pytest.approx(best, rel=1e-9)
    for other in every_comparator(m, 4):
        if other.selected_condition_number is not None:
            assert record.selected_condition_number <= other.selected_condition_number + 1e-9


def test_exact_enumeration_is_not_labelled_an_oracle() -> None:
    """It uses no privileged information -- only exhaustive search of a small space."""
    record = exact_enumeration_comparator(matrix(10, 3), 4, budget=budget())
    assert record is not None
    assert record.method_class == "exact_small_problem_solver"
    assert record.uses_privileged_information is False


def test_the_row_cap_bounds_the_subset_count_which_is_the_real_cost() -> None:
    """Measured: C(20,10) = 184,756 subsets at ~3.6s; C(22,11) = 705,432 at ~14s."""
    import math

    record = exact_enumeration_comparator(matrix(10, 3), 4, budget=budget())
    assert record is not None
    assert record.metadata["max_subsets_bounded_by_row_cap"] == math.comb(20, 10) == 184756


# --- the word "oracle" ------------------------------------------------------


def test_no_emitted_record_contains_the_unqualified_word_oracle() -> None:
    """Qualified names like true_support_diagnostic_oracle are fine; bare is not."""
    for record in every_comparator(matrix()):
        encoded = json.dumps(record.as_dict())
        assert not re.search(r"\boracle\b", encoded), encoded


def test_the_regex_distinguishes_qualified_from_bare() -> None:
    """Guard the guard: the assertion above must actually be able to fail."""
    assert re.search(r"\boracle\b", '{"note": "the oracle wins"}')
    assert not re.search(r"\boracle\b", '{"c": "true_support_diagnostic_oracle"}')


# --- validation -------------------------------------------------------------


def test_invalid_matrices_and_counts_are_refused() -> None:
    with pytest.raises(ShapeValidationError, match="two-dimensional"):
        raw_local_design(np.ones(4), 2, budget=budget())
    with pytest.raises(ScopeValidationError, match=r"must lie in \[1, 12\]"):
        raw_local_design(matrix(), 99, budget=budget())
    bad = matrix().copy()
    bad[0, 0] = np.nan
    with pytest.raises(ScopeValidationError, match="finite"):
        raw_local_design(bad, 2, budget=budget())


def test_random_and_d_optimal_seeds_must_be_integers() -> None:
    with pytest.raises(ScopeValidationError, match="seed must be an integer"):
        random_budget_matched_design(matrix(), 5, budget=budget(), seed=True)
    with pytest.raises(ScopeValidationError, match="seed must be an int or None"):
        d_optimal_exchange_comparator(matrix(), 5, budget=budget(), seed="7")


def test_translation_orbit_requires_shifts() -> None:
    with pytest.raises(ScopeValidationError, match="shifts must be"):
        translation_orbit_design(matrix(), 5, budget=budget(), shifts=[])
