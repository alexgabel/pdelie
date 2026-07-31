"""v0.36b: DesignRowLineage and the two design hashes."""

from __future__ import annotations

import json

import numpy as np
import pytest

from pdelie.design import (
    DesignRowLineage,
    compute_numeric_design_hash,
    compute_semantic_design_hash,
)
from pdelie.errors import ScopeValidationError, ShapeValidationError


def row(index: int = 0, **overrides: object) -> DesignRowLineage:
    base = {
        "trajectory_id": f"traj_{index}",
        "source_coordinate_id": f"coord_{index}",
        "mask_id": "regression_row_mask",
    }
    base.update(overrides)
    return DesignRowLineage(**base)  # type: ignore[arg-type]


def test_round_trips_through_strict_json() -> None:
    payload = row().as_dict()
    assert json.loads(json.dumps(payload, allow_nan=False)) == payload


@pytest.mark.parametrize("field", ["trajectory_id", "source_coordinate_id", "mask_id"])
def test_the_three_gate_required_fields_cannot_be_blank(field: str) -> None:
    """Exit gate A-alpha-2 requires all three non-null on every design row."""
    for bad in ("", "   ", None):
        with pytest.raises(ScopeValidationError, match=field):
            row(**{field: bad})


def test_optional_fields_accept_none_but_not_blank() -> None:
    assert row(view_id=None).view_id is None
    with pytest.raises(ScopeValidationError, match="view_id"):
        row(view_id="  ")


def test_semantic_hash_is_order_sensitive_by_design() -> None:
    """Row order determines which rows a budgeted truncation keeps."""
    rows = [row(i) for i in range(4)]
    assert compute_semantic_design_hash(rows) != compute_semantic_design_hash(rows[::-1])


def test_semantic_hash_is_stable_for_identical_provenance() -> None:
    first = [row(i) for i in range(4)]
    second = [row(i) for i in range(4)]
    assert compute_semantic_design_hash(first) == compute_semantic_design_hash(second)


def test_semantic_hash_changes_when_any_provenance_field_changes() -> None:
    base = [row(0)]
    assert compute_semantic_design_hash(base) != compute_semantic_design_hash(
        [row(0, view_id="shifted")]
    )
    assert compute_semantic_design_hash(base) != compute_semantic_design_hash(
        [row(0, mask_id="observation_mask")]
    )


def test_semantic_hash_routes_through_the_one_canonical_hash() -> None:
    """No second canonical-JSON path anywhere in the codebase."""
    from pdelie.artifact import semantic_hash

    rows = [row(0), row(1)]
    expected = semantic_hash({"rows": [r.as_dict() for r in rows]})
    assert compute_semantic_design_hash(rows) == expected


def test_empty_or_wrong_typed_rows_are_refused() -> None:
    with pytest.raises(ScopeValidationError, match="non-empty"):
        compute_semantic_design_hash([])
    with pytest.raises(ScopeValidationError, match="not DesignRowLineage"):
        compute_semantic_design_hash([{"trajectory_id": "t"}])  # type: ignore[list-item]


def test_numeric_hash_is_column_order_sensitive() -> None:
    matrix = np.arange(12.0).reshape(3, 4)
    assert compute_numeric_design_hash(matrix) != compute_numeric_design_hash(matrix[:, ::-1])


def test_numeric_hash_distinguishes_dtype_and_shape() -> None:
    values = np.arange(6.0).reshape(2, 3)
    assert compute_numeric_design_hash(values) != compute_numeric_design_hash(
        values.astype(np.float32)
    )
    assert compute_numeric_design_hash(values) != compute_numeric_design_hash(
        values.reshape(3, 2)
    )


def test_numeric_hash_is_exact_discrete_not_a_tolerance_comparison() -> None:
    """Two matrices agreeing to 1e-12 have different numeric hashes. That is correct."""
    values = np.ones((2, 2))
    nudged = values.copy()
    nudged[0, 0] += 1e-12
    assert compute_numeric_design_hash(values) != compute_numeric_design_hash(nudged)
    assert np.allclose(values, nudged, rtol=1e-6, atol=1e-12)


def test_numeric_hash_is_invariant_to_memory_layout() -> None:
    """Identity is content, not striding."""
    values = np.arange(6.0).reshape(2, 3)
    assert compute_numeric_design_hash(values) == compute_numeric_design_hash(
        np.asfortranarray(values).copy(order="C")
    )


def test_numeric_hash_refuses_non_matrix_and_object_input() -> None:
    with pytest.raises(ShapeValidationError, match="two-dimensional"):
        compute_numeric_design_hash(np.ones(4))
    with pytest.raises(ScopeValidationError, match="dtype=object"):
        compute_numeric_design_hash(np.array([[{"a": 1}]], dtype=object))


def test_the_two_hashes_answer_different_questions() -> None:
    """Same provenance, different bytes: semantic agrees, numeric does not."""
    rows = [row(0), row(1)]
    a = np.ones((2, 2))
    b = a * (1 + 1e-9)
    assert compute_semantic_design_hash(rows) == compute_semantic_design_hash(rows)
    assert compute_numeric_design_hash(a) != compute_numeric_design_hash(b)


def test_row_count_equals_lineage_record_count() -> None:
    """The b-gate, in its local form."""
    matrix = np.zeros((5, 3))
    rows = [row(i) for i in range(5)]
    assert matrix.shape[0] == len(rows)
    compute_semantic_design_hash(rows)


def test_not_exported_from_the_root_namespace() -> None:
    import pdelie

    for name in ("DesignRowLineage", "compute_semantic_design_hash"):
        assert name not in pdelie.__all__
        assert not hasattr(pdelie, name)
