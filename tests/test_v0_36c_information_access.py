"""v0.36c: information-access declarations are mandatory and closed."""

from __future__ import annotations

import pytest

from pdelie.design import (
    MANDATORY_ACCESS_KEYS,
    METHOD_CLASSES,
    DesignBudget,
    DesignCandidateRecord,
    validate_information_access,
)
from pdelie.errors import ScopeValidationError

FULL_ACCESS = {
    "uses_true_support": False,
    "uses_true_coefficients": False,
    "requires_full_domain": False,
    "requires_unobserved_rows": False,
    "requires_heldout_data": False,
    "uses_future_time": False,
}


def budget() -> DesignBudget:
    return DesignBudget(
        budget_value=5.0, budget_unit="rows", num_views=1, allocation_policy="uniform",
        grouping_policy="by_trajectory", duplicate_policy="retain",
        row_weight_policy="unit", train_only=True,
    )


def record(**overrides) -> DesignCandidateRecord:
    base = {
        "design_id": "d", "method_name": "m", "method_class": "attainable_policy",
        "selected_row_indices": (0, 1), "budget": budget(),
        "information_access": dict(FULL_ACCESS),
    }
    base.update(overrides)
    return DesignCandidateRecord(**base)


def test_all_six_flags_are_mandatory() -> None:
    assert len(MANDATORY_ACCESS_KEYS) == 6


@pytest.mark.parametrize("missing", sorted(MANDATORY_ACCESS_KEYS))
def test_a_missing_flag_raises_rather_than_defaulting(missing: str) -> None:
    """Silence is not a declaration: 'we did not think about it' and 'we do not
    use it' are different claims and only one is evidence."""
    access = {k: v for k, v in FULL_ACCESS.items() if k != missing}
    with pytest.raises(ScopeValidationError, match="missing required keys"):
        validate_information_access(access)
    with pytest.raises(ScopeValidationError, match="missing required keys"):
        record(information_access=access)


def test_unknown_flags_are_refused() -> None:
    """A closed vocabulary is what makes two records comparable."""
    with pytest.raises(ScopeValidationError, match="unknown keys"):
        validate_information_access({**FULL_ACCESS, "reads_the_future": True})


def test_flags_must_be_strict_bools() -> None:
    with pytest.raises(ScopeValidationError, match="must be a bool"):
        validate_information_access({**FULL_ACCESS, "uses_true_support": 1})


def test_non_mapping_access_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="must be a mapping"):
        validate_information_access(["uses_true_support"])


def test_every_candidate_declares_at_least_six_flags() -> None:
    """The c-gate, in its literal form."""
    candidate = record()
    assert len(candidate.information_access) >= 6
    validate_information_access(candidate.information_access)


def test_privileged_information_is_derived_from_the_flags() -> None:
    assert record().uses_privileged_information is False
    for flag in ("uses_true_support", "uses_true_coefficients", "uses_future_time"):
        assert record(information_access={**FULL_ACCESS, flag: True}).uses_privileged_information


def test_requiring_the_full_domain_is_not_by_itself_privileged() -> None:
    """A practitioner may well have the full domain; not knowing the answer is
    the distinction that matters."""
    candidate = record(information_access={**FULL_ACCESS, "requires_full_domain": True})
    assert candidate.uses_privileged_information is False


def test_the_oracle_class_is_privileged_by_construction() -> None:
    candidate = record(method_class="true_support_diagnostic_oracle")
    assert candidate.uses_privileged_information is True


def test_bare_oracle_is_not_a_method_class() -> None:
    """Four situations, four names. Collapsing them turns measurement into verdict."""
    assert "oracle" not in METHOD_CLASSES
    assert len(METHOD_CLASSES) == 4
    with pytest.raises(ScopeValidationError, match="not one of"):
        record(method_class="oracle")


def test_record_round_trips_and_carries_the_derived_flag() -> None:
    import json

    payload = record().as_dict()
    assert json.loads(json.dumps(payload, allow_nan=False)) == payload
    assert payload["uses_privileged_information"] is False
    assert payload["num_rows_selected"] == 2


def test_duplicate_row_indices_are_refused() -> None:
    with pytest.raises(ScopeValidationError, match="must not repeat"):
        record(selected_row_indices=(0, 0))


def test_not_exported_from_the_root_namespace() -> None:
    import pdelie

    for name in ("DesignCandidateRecord", "validate_information_access", "attainability_report"):
        assert name not in pdelie.__all__
        assert not hasattr(pdelie, name)
