"""Tests for the v0.30c finite_difference derivative backend.

Manufactured analytic field tests use closed-form derivatives, not `np.gradient`
itself — testing the backend against itself would be meaningless. See
`docs/design/DERIVATIVE_BACKEND_POLICY.md`.
"""
from __future__ import annotations

import json
import math

import numpy as np
import pytest

from pdelie._boundary import normalize_x_boundary_condition
from pdelie.contracts import ALLOWED_DERIVATIVE_BACKENDS
from pdelie.data import from_numpy
from pdelie.derivatives import compute_finite_difference_derivatives
from pdelie.errors import ScopeValidationError


def _nonperiodic_metadata(*, x_boundary: str | dict = "dirichlet") -> dict:
    return {
        "boundary_conditions": {"x": x_boundary},
        "coordinate_system": "cartesian",
        "grid_regularity": "uniform",
        "grid_type": "rectilinear",
        "parameter_tags": {},
    }


def _polynomial_field(
    *,
    n_t: int = 17,
    n_x: int = 33,
    t_max: float = 1.0,
    x_max: float = 2.0,
    x_boundary: str | dict = "dirichlet",
):
    """u(t, x) = t^2 + x^2 + t * x on a uniform nonperiodic grid."""
    t = np.linspace(0.0, t_max, n_t, dtype=float)
    x = np.linspace(0.0, x_max, n_x, dtype=float)
    T, X = np.meshgrid(t, x, indexing="ij")
    values = (T**2 + X**2 + T * X)[None, ..., None]
    return (
        from_numpy(
            values,
            dims=("batch", "time", "x", "var"),
            coords={"time": t, "x": x},
            var_name="u",
            metadata=_nonperiodic_metadata(x_boundary=x_boundary),
        ),
        t,
        x,
    )


def test_polynomial_derivatives_are_exact_in_interior() -> None:
    """For u = t^2 + x^2 + t*x, edge-order-2 FD recovers u_t, u_x, u_xx exactly.

    np.gradient with edge_order=2 is exact for polynomials of degree <=2.
    """
    field, t, x = _polynomial_field()
    d = compute_finite_difference_derivatives(field, max_spatial_order=2)

    # u_t = 2t + x, u_x = 2x + t, u_xx = 2
    T, X = np.meshgrid(t, x, indexing="ij")
    expected_u_t = (2.0 * T + X)[None, ..., None]
    expected_u_x = (2.0 * X + T)[None, ..., None]
    expected_u_xx = np.full_like(expected_u_t, 2.0)

    np.testing.assert_allclose(d.derivatives["u_t"], expected_u_t, atol=1e-10)
    np.testing.assert_allclose(d.derivatives["u_x"], expected_u_x, atol=1e-10)
    np.testing.assert_allclose(d.derivatives["u_xx"], expected_u_xx, atol=1e-9)


def test_max_spatial_order_1_emits_only_first_derivatives() -> None:
    field, _, _ = _polynomial_field()
    d = compute_finite_difference_derivatives(field, max_spatial_order=1)
    assert set(d.derivatives.keys()) == {"u_t", "u_x"}
    assert d.config["spatial_max_order"] == 1


def test_derivative_batch_validates_against_field() -> None:
    field, _, _ = _polynomial_field()
    d = compute_finite_difference_derivatives(field, max_spatial_order=2)
    # Already called inside compute_finite_difference_derivatives, but re-asserting:
    d.validate_against(field)
    assert d.backend == "finite_difference"
    assert d.backend in ALLOWED_DERIVATIVE_BACKENDS


def test_backend_config_carries_required_fields() -> None:
    field, _, _ = _polynomial_field(x_boundary="neumann")
    d = compute_finite_difference_derivatives(field)
    assert d.config["spatial_method"] == "finite_difference_centered"
    assert d.config["temporal_method"] == "finite_difference"
    assert d.config["stencil_edge_order"] == 2
    assert d.config["boundary_handling"] == "neumann"
    assert d.config["spatial_max_order"] == 2
    assert d.config["backend_selected_by_boundary_condition"] is False
    assert d.config["backend_selection_reason"] is None
    assert d.config["recommended_residual_domain_policy"] == "interior_only"
    assert d.config["recommended_boundary_trim_width"] == 4
    assert "neumann" in d.boundary_assumptions
    assert d.diagnostics["x_points"] == field.values.shape[2]
    assert d.diagnostics["time_points"] == field.values.shape[1]
    for key in ("dx", "dt"):
        assert math.isfinite(d.diagnostics[key])


def test_derivative_batch_is_strict_json_compatible() -> None:
    field, _, _ = _polynomial_field()
    d = compute_finite_difference_derivatives(field)
    payload = d.to_dict()
    # No NaN; round-trippable.
    assert json.loads(json.dumps(payload, allow_nan=False)) == payload


def test_rejects_periodic_input() -> None:
    """Periodic data must go through spectral_fd. The FD backend explicitly rejects it."""
    t = np.linspace(0.0, 1.0, 17, dtype=float)
    x = np.linspace(0.0, 2.0 * np.pi, 16, endpoint=False, dtype=float)
    values = np.zeros((1, 17, 16, 1), dtype=float)
    field = from_numpy(
        values,
        dims=("batch", "time", "x", "var"),
        coords={"time": t, "x": x},
        var_name="u",
        metadata={
            "boundary_conditions": {"x": "periodic"},
            "coordinate_system": "cartesian",
            "grid_regularity": "uniform",
            "grid_type": "rectilinear",
            "parameter_tags": {},
        },
    )
    with pytest.raises(ScopeValidationError, match="rejects periodic"):
        compute_finite_difference_derivatives(field)


def test_rejects_max_spatial_order_3() -> None:
    field, _, _ = _polynomial_field()
    with pytest.raises(ScopeValidationError, match="max_spatial_order must be 1 or 2"):
        compute_finite_difference_derivatives(field, max_spatial_order=3)


def test_rejects_max_spatial_order_4() -> None:
    field, _, _ = _polynomial_field()
    with pytest.raises(ScopeValidationError, match="max_spatial_order must be 1 or 2"):
        compute_finite_difference_derivatives(field, max_spatial_order=4)


def test_rejects_bool_max_spatial_order() -> None:
    field, _, _ = _polynomial_field()
    # True passes int() to 1 but is explicitly disallowed.
    with pytest.raises(ScopeValidationError, match="max_spatial_order"):
        compute_finite_difference_derivatives(field, max_spatial_order=True)


def test_rejects_nonuniform_x_grid() -> None:
    n_t = 17
    t = np.linspace(0.0, 1.0, n_t, dtype=float)
    x = np.array([0.0, 0.2, 0.5, 0.9, 1.3, 1.6, 1.7, 1.8, 2.0], dtype=float)
    # from_numpy rejects nonuniform x at ingestion. Build FieldBatch directly to
    # exercise the backend's uniform-x check.
    # Actually from_numpy checks _is_uniform; we can satisfy the FieldBatch contract
    # only with a uniform grid. Use a uniform grid via from_numpy, then mutate.
    field = from_numpy(
        np.zeros((1, n_t, 9, 1), dtype=float),
        dims=("batch", "time", "x", "var"),
        coords={"time": t, "x": np.linspace(0.0, 2.0, 9, dtype=float)},
        var_name="u",
        metadata=_nonperiodic_metadata(),
    )
    # Mutate the x coords to make them nonuniform; bypass validate() because we
    # explicitly want to exercise the backend's own check.
    field.coords["x"] = x
    # FieldBatch.validate() (called first by the backend) catches nonuniform spatial
    # grids at the canonical contract layer. The error message is the contract's.
    with pytest.raises(ScopeValidationError, match="uniform rectilinear"):
        compute_finite_difference_derivatives(field)


def test_rejects_nonuniform_time_grid() -> None:
    field, _, _ = _polynomial_field()
    field.coords["time"] = np.array([0.0, 0.1, 0.3, 0.45, 0.55, 0.7, 0.8, 0.9, 0.95, 1.0,
                                      1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7], dtype=float)[: field.values.shape[1]]
    # Time-axis uniformity is checked by the FD backend itself (the contract layer
    # only enforces it for SPATIAL_DIMS like x).
    with pytest.raises(ScopeValidationError, match="uniform time grid"):
        compute_finite_difference_derivatives(field)


def test_rejects_too_few_x_points() -> None:
    t = np.linspace(0.0, 1.0, 5, dtype=float)
    x = np.linspace(0.0, 1.0, 4, dtype=float)
    values = np.zeros((1, 5, 4, 1), dtype=float)
    field = from_numpy(
        values,
        dims=("batch", "time", "x", "var"),
        coords={"time": t, "x": x},
        var_name="u",
        metadata=_nonperiodic_metadata(),
    )
    # Drop x to 2 points
    field.values = field.values[..., :2, :]
    field.coords["x"] = x[:2]
    with pytest.raises(ScopeValidationError, match="at least 3 x-points"):
        compute_finite_difference_derivatives(field)


def test_rejects_too_few_time_points() -> None:
    t = np.linspace(0.0, 1.0, 5, dtype=float)
    x = np.linspace(0.0, 1.0, 5, dtype=float)
    values = np.zeros((1, 5, 5, 1), dtype=float)
    field = from_numpy(
        values,
        dims=("batch", "time", "x", "var"),
        coords={"time": t, "x": x},
        var_name="u",
        metadata=_nonperiodic_metadata(),
    )
    field.values = field.values[:, :2, :, :]
    field.coords["time"] = t[:2]
    with pytest.raises(ScopeValidationError, match="at least 3 time points"):
        compute_finite_difference_derivatives(field)


def test_accepts_structured_dirichlet_spec() -> None:
    structured = normalize_x_boundary_condition({
        "type": "dirichlet",
        "left": {"value": 0.0, "time_dependent": False, "source": "user_supplied"},
        "right": {"value": 1.0, "time_dependent": False, "source": "user_supplied"},
    })
    field, _, _ = _polynomial_field(x_boundary=structured)
    d = compute_finite_difference_derivatives(field)
    assert d.config["boundary_handling"] == "dirichlet"


def test_accepts_neumann_and_open_unknown_legacy_strings() -> None:
    for bc in ("neumann", "open_unknown"):
        field, _, _ = _polynomial_field(x_boundary=bc)
        d = compute_finite_difference_derivatives(field)
        assert d.config["boundary_handling"] == bc
