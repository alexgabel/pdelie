"""Tests for the v0.30c `compute_derivatives` backend dispatcher."""
from __future__ import annotations

import numpy as np
import pytest

from pdelie.data import from_numpy, generate_heat_1d_field_batch
from pdelie.derivatives import compute_derivatives
from pdelie.errors import ScopeValidationError


def _nonperiodic_metadata(*, x_boundary: str = "dirichlet") -> dict:
    return {
        "boundary_conditions": {"x": x_boundary},
        "coordinate_system": "cartesian",
        "grid_regularity": "uniform",
        "grid_type": "rectilinear",
        "parameter_tags": {},
    }


def _nonperiodic_field(*, x_boundary: str = "dirichlet"):
    n_t, n_x = 9, 16
    t = np.linspace(0.0, 1.0, n_t, dtype=float)
    x = np.linspace(0.0, 1.0, n_x, dtype=float)
    values = np.zeros((1, n_t, n_x, 1), dtype=float)
    return from_numpy(
        values,
        dims=("batch", "time", "x", "var"),
        coords={"time": t, "x": x},
        var_name="u",
        metadata=_nonperiodic_metadata(x_boundary=x_boundary),
    )


# --- backend="auto" path -----------------------------------------------------


def test_auto_on_periodic_routes_to_spectral_fd_and_records_reason() -> None:
    field = generate_heat_1d_field_batch(batch_size=1, num_times=5, num_points=16, seed=0)
    d = compute_derivatives(field, backend="auto", max_spatial_order=2)
    assert d.backend == "spectral_fd"
    assert d.config["backend_selected_by_boundary_condition"] is True
    assert d.config["backend_selection_reason"] == "periodic_x_uses_spectral_fd"


def test_auto_on_dirichlet_routes_to_finite_difference_and_records_reason() -> None:
    field = _nonperiodic_field(x_boundary="dirichlet")
    d = compute_derivatives(field, backend="auto", max_spatial_order=2)
    assert d.backend == "finite_difference"
    assert d.config["backend_selected_by_boundary_condition"] is True
    assert d.config["backend_selection_reason"] == "nonperiodic_x_uses_finite_difference"


def test_auto_on_neumann_routes_to_finite_difference() -> None:
    field = _nonperiodic_field(x_boundary="neumann")
    d = compute_derivatives(field, backend="auto")
    assert d.backend == "finite_difference"
    assert d.config["backend_selection_reason"] == "nonperiodic_x_uses_finite_difference"


def test_auto_on_open_unknown_routes_to_finite_difference() -> None:
    field = _nonperiodic_field(x_boundary="open_unknown")
    d = compute_derivatives(field, backend="auto")
    assert d.backend == "finite_difference"
    assert d.config["backend_selection_reason"] == "nonperiodic_x_uses_finite_difference"


# --- explicit backend path --------------------------------------------------


def test_explicit_finite_difference_on_nonperiodic_works() -> None:
    field = _nonperiodic_field()
    d = compute_derivatives(field, backend="finite_difference")
    assert d.backend == "finite_difference"
    # Explicit backend selection: dispatcher does NOT mark backend_selected_by_boundary_condition.
    assert d.config["backend_selected_by_boundary_condition"] is False
    assert d.config["backend_selection_reason"] is None


def test_explicit_spectral_fd_on_periodic_works() -> None:
    field = generate_heat_1d_field_batch(batch_size=1, num_times=5, num_points=16, seed=1)
    d = compute_derivatives(field, backend="spectral_fd")
    assert d.backend == "spectral_fd"


def test_explicit_spectral_fd_on_nonperiodic_raises_and_does_not_fall_back() -> None:
    field = _nonperiodic_field()
    with pytest.raises(ScopeValidationError, match="periodic"):
        compute_derivatives(field, backend="spectral_fd")


def test_explicit_finite_difference_on_periodic_raises_and_does_not_fall_back() -> None:
    field = generate_heat_1d_field_batch(batch_size=1, num_times=5, num_points=16, seed=2)
    with pytest.raises(ScopeValidationError, match="rejects periodic"):
        compute_derivatives(field, backend="finite_difference")


# --- bad backend names ------------------------------------------------------


def test_unknown_backend_raises() -> None:
    field = _nonperiodic_field()
    with pytest.raises(ScopeValidationError, match="backend must be one of"):
        compute_derivatives(field, backend="weak")
    with pytest.raises(ScopeValidationError, match="backend must be one of"):
        compute_derivatives(field, backend="nonsense")


def test_non_string_backend_raises() -> None:
    field = _nonperiodic_field()
    with pytest.raises(ScopeValidationError, match="backend must be one of"):
        compute_derivatives(field, backend=42)  # type: ignore[arg-type]


# --- order propagation ------------------------------------------------------


def test_max_spatial_order_propagates_to_finite_difference() -> None:
    field = _nonperiodic_field()
    d1 = compute_derivatives(field, backend="auto", max_spatial_order=1)
    assert set(d1.derivatives.keys()) == {"u_t", "u_x"}
    d2 = compute_derivatives(field, backend="auto", max_spatial_order=2)
    assert set(d2.derivatives.keys()) == {"u_t", "u_x", "u_xx"}


def test_finite_difference_high_order_rejected_via_dispatcher() -> None:
    field = _nonperiodic_field()
    with pytest.raises(ScopeValidationError, match="max_spatial_order"):
        compute_derivatives(field, backend="auto", max_spatial_order=3)


# --- auto selection annotation does not lie on explicit calls ---------------


def test_auto_annotation_only_set_when_backend_is_auto() -> None:
    """The `backend_selected_by_boundary_condition` flag must mean "auto did it",
    not "any periodic check happened". Explicit calls must not claim auto."""
    periodic = generate_heat_1d_field_batch(batch_size=1, num_times=5, num_points=16, seed=3)
    d = compute_derivatives(periodic, backend="spectral_fd")
    assert d.config.get("backend_selected_by_boundary_condition", False) is False

    nonperiodic = _nonperiodic_field()
    d2 = compute_derivatives(nonperiodic, backend="finite_difference")
    assert d2.config["backend_selected_by_boundary_condition"] is False
