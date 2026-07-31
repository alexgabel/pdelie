"""v0.36b: ObservationOperatorSpec."""

from __future__ import annotations

import json

import pytest

from pdelie.errors import ScopeValidationError
from pdelie.observation import OBSERVATION_OPERATOR_KINDS, ObservationOperatorSpec


def spec(**overrides: object) -> ObservationOperatorSpec:
    base = {"operator_kind": "identity", "observed_point_count": 64, "total_point_count": 64}
    base.update(overrides)
    return ObservationOperatorSpec(**base)  # type: ignore[arg-type]


def test_round_trips_through_strict_json() -> None:
    payload = spec().as_dict()
    assert json.loads(json.dumps(payload, allow_nan=False)) == payload


@pytest.mark.parametrize("kind", OBSERVATION_OPERATOR_KINDS)
def test_every_declared_kind_is_constructible(kind: str) -> None:
    observed = 64 if kind == "identity" else 32
    assert spec(operator_kind=kind, observed_point_count=observed).operator_kind == kind


def test_unknown_operator_kind_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="is not one of"):
        spec(operator_kind="telepathy")


def test_cannot_observe_more_points_than_exist() -> None:
    with pytest.raises(ScopeValidationError, match="exceeds"):
        spec(operator_kind="masked_subsample", observed_point_count=65, total_point_count=64)


def test_identity_must_observe_every_point() -> None:
    """Declaring 'identity' while subsampling would misreport what was seen."""
    with pytest.raises(ScopeValidationError, match="must observe every point"):
        spec(observed_point_count=32)


def test_observed_fraction_is_reported() -> None:
    assert spec(operator_kind="masked_subsample", observed_point_count=16).observed_fraction == 0.25
    assert spec(observed_point_count=0, total_point_count=0).observed_fraction == 0.0


def test_identity_distinguishes_different_observations() -> None:
    a = spec(operator_kind="masked_subsample", observed_point_count=32, mask_id="m1")
    b = spec(operator_kind="masked_subsample", observed_point_count=32, mask_id="m2")
    assert a.identity() != b.identity()


def test_blank_optional_strings_are_refused() -> None:
    with pytest.raises(ScopeValidationError, match="mask_id"):
        spec(mask_id="   ")


def test_not_exported_from_the_root_namespace() -> None:
    import pdelie

    assert "ObservationOperatorSpec" not in pdelie.__all__
    assert not hasattr(pdelie, "ObservationOperatorSpec")


def test_non_integer_counts_are_refused() -> None:
    with pytest.raises(ScopeValidationError, match="observed_point_count must be an integer"):
        spec(observed_point_count=1.5)
    with pytest.raises(ScopeValidationError, match="non-negative"):
        spec(operator_kind="masked_subsample", observed_point_count=-1)


def test_non_mapping_metadata_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="metadata must be a mapping"):
        spec(metadata=["a"])
