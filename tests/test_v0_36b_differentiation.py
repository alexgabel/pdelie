"""v0.36b: DifferentiationPolicySpec."""

from __future__ import annotations

import json

import pytest

from pdelie.differentiation import (
    DIFFERENTIATION_BACKENDS,
    DIFFERENTIATION_BOUNDARY_HANDLING,
    DifferentiationPolicySpec,
)
from pdelie.errors import ScopeValidationError


def spec(**overrides: object) -> DifferentiationPolicySpec:
    base = {
        "backend": "spectral_fd",
        "max_spatial_order": 2,
        "boundary_handling": "periodic_wrap",
        "stencil_half_width": 0,
    }
    base.update(overrides)
    return DifferentiationPolicySpec(**base)  # type: ignore[arg-type]


def test_round_trips_through_strict_json() -> None:
    payload = spec().as_dict()
    assert json.loads(json.dumps(payload, allow_nan=False)) == payload


def test_declared_vocabularies_are_the_ones_the_repo_ships() -> None:
    assert DIFFERENTIATION_BACKENDS == ("spectral_fd", "finite_difference")
    assert "interior_only_trim" in DIFFERENTIATION_BOUNDARY_HANDLING


def test_spectral_backend_requires_periodic_wrap() -> None:
    """Nonperiodic data dispatches to finite_difference; the spec cannot claim otherwise."""
    with pytest.raises(ScopeValidationError, match="only valid under periodic_wrap"):
        spec(boundary_handling="one_sided_stencil")


def test_finite_difference_with_positive_order_needs_a_stencil_width() -> None:
    """The half-width is what determines derivative validity near a mask edge."""
    with pytest.raises(ScopeValidationError, match="positive stencil_half_width"):
        spec(backend="finite_difference", boundary_handling="one_sided_stencil", stencil_half_width=0)


def test_valid_finite_difference_policy_constructs() -> None:
    policy = spec(
        backend="finite_difference", boundary_handling="interior_only_trim", stencil_half_width=2
    )
    assert policy.stencil_half_width == 2


def test_unknown_backend_or_boundary_handling_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="backend"):
        spec(backend="autodiff")
    with pytest.raises(ScopeValidationError, match="boundary_handling"):
        spec(boundary_handling="wishful")


def test_negative_orders_are_refused() -> None:
    with pytest.raises(ScopeValidationError, match="non-negative"):
        spec(max_spatial_order=-1)
    with pytest.raises(ScopeValidationError, match="must be an integer"):
        spec(stencil_half_width=True)


def test_identity_distinguishes_stencil_widths() -> None:
    a = spec(backend="finite_difference", boundary_handling="interior_only_trim", stencil_half_width=1)
    b = spec(backend="finite_difference", boundary_handling="interior_only_trim", stencil_half_width=2)
    assert a.identity() != b.identity()


def test_not_exported_from_the_root_namespace() -> None:
    import pdelie

    assert "DifferentiationPolicySpec" not in pdelie.__all__
    assert not hasattr(pdelie, "DifferentiationPolicySpec")


def test_the_two_specs_are_separate_types() -> None:
    """v0.33c's defect was conflating what was observed with where a stencil is valid."""
    from pdelie.observation import ObservationOperatorSpec

    assert DifferentiationPolicySpec is not ObservationOperatorSpec
    assert set(spec().as_dict()) & {"mask_id", "sensor_layout"} == set()


def test_blank_temporal_method_and_non_mapping_metadata_are_refused() -> None:
    with pytest.raises(ScopeValidationError, match="temporal_method"):
        spec(temporal_method="  ")
    with pytest.raises(ScopeValidationError, match="metadata must be a mapping"):
        spec(metadata=["a"])
