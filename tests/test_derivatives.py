from __future__ import annotations

import numpy as np
import pytest

from pdelie import FieldBatch, ScopeValidationError
from pdelie.data.heat_1d import evaluate_heat_fourier_series
from pdelie.derivatives import compute_spectral_fd_derivatives


def make_exact_heat_field() -> tuple[FieldBatch, np.ndarray, np.ndarray, np.ndarray]:
    x = np.linspace(0.0, 2.0 * np.pi, 64, endpoint=False)
    t = np.linspace(0.0, 0.4, 33)
    cosine = np.array([[0.7, -0.25]])
    sine = np.array([[0.35, 0.15]])
    diffusivity = 0.1
    values = evaluate_heat_fourier_series(
        x=x,
        t=t,
        cosine_coefficients=cosine,
        sine_coefficients=sine,
        diffusivity=diffusivity,
    )
    field = FieldBatch(
        values=values[..., None],
        dims=("batch", "time", "x", "var"),
        coords={"time": t, "x": x},
        var_names=["u"],
        metadata={
            "boundary_conditions": {"x": "periodic"},
            "coordinate_system": "cartesian",
            "grid_regularity": "uniform",
            "grid_type": "rectilinear",
            "parameter_tags": {"nu": diffusivity},
        },
        preprocess_log=[],
    )

    modes = np.arange(1, cosine.shape[1] + 1, dtype=float)
    decay = np.exp(-diffusivity * np.square(modes)[None, :] * t[:, None])
    cos_kx = np.cos(np.outer(modes, x))
    sin_kx = np.sin(np.outer(modes, x))

    ux_modes = (-cosine[:, None, :, None] * modes[None, None, :, None] * sin_kx[None, None, :, :])
    ux_modes += sine[:, None, :, None] * modes[None, None, :, None] * cos_kx[None, None, :, :]
    u_x = np.sum(decay[None, :, :, None] * ux_modes, axis=2)[..., None]

    uxx_modes = (-cosine[:, None, :, None] * np.square(modes)[None, None, :, None] * cos_kx[None, None, :, :])
    uxx_modes += -sine[:, None, :, None] * np.square(modes)[None, None, :, None] * sin_kx[None, None, :, :]
    u_xx = np.sum(decay[None, :, :, None] * uxx_modes, axis=2)[..., None]
    uxxx_modes = cosine[:, None, :, None] * (modes[None, None, :, None] ** 3) * sin_kx[None, None, :, :]
    uxxx_modes += -sine[:, None, :, None] * (modes[None, None, :, None] ** 3) * cos_kx[None, None, :, :]
    u_xxx = np.sum(decay[None, :, :, None] * uxxx_modes, axis=2)[..., None]
    u_t = diffusivity * u_xx

    return field, u_x, u_t, u_xxx


def test_spectral_fd_matches_analytic_derivatives() -> None:
    field, expected_u_x, expected_u_t, _ = make_exact_heat_field()
    derivatives = compute_spectral_fd_derivatives(field)
    np.testing.assert_allclose(derivatives.derivatives["u_x"], expected_u_x, atol=1e-10, rtol=1e-10)
    np.testing.assert_allclose(derivatives.derivatives["u_t"], expected_u_t, atol=1e-3, rtol=1e-3)
    np.testing.assert_allclose(
        derivatives.derivatives["u_t"],
        field.metadata["parameter_tags"]["nu"] * derivatives.derivatives["u_xx"],
        atol=1e-3,
        rtol=1e-3,
    )


def test_spectral_fd_records_provenance() -> None:
    field, _, _, _ = make_exact_heat_field()
    derivatives = compute_spectral_fd_derivatives(field)
    assert derivatives.backend == "spectral_fd"
    assert derivatives.config["spatial_method"] == "spectral"
    assert derivatives.config["temporal_method"] == "finite_difference"
    assert "periodic" in derivatives.boundary_assumptions
    assert derivatives.diagnostics["x_points"] == field.coords["x"].size


def test_spectral_fd_rejects_nonperiodic_boundary_conditions() -> None:
    field, _, _, _ = make_exact_heat_field()
    field.metadata["boundary_conditions"] = {"x": "dirichlet"}
    with pytest.raises(ScopeValidationError):
        compute_spectral_fd_derivatives(field)


def test_spectral_fd_default_and_explicit_second_order_are_compatible() -> None:
    field, _, _, _ = make_exact_heat_field()

    default = compute_spectral_fd_derivatives(field)
    explicit = compute_spectral_fd_derivatives(field, max_spatial_order=2)

    assert set(default.derivatives) == {"u_t", "u_x", "u_xx"}
    assert set(explicit.derivatives) == set(default.derivatives)
    assert explicit.config == default.config
    assert explicit.diagnostics == default.diagnostics
    for name in default.derivatives:
        np.testing.assert_allclose(explicit.derivatives[name], default.derivatives[name], atol=0.0, rtol=0.0)
    assert "spatial_max_order" not in default.config


def test_spectral_fd_first_order_emits_only_time_and_first_spatial_derivative() -> None:
    field, expected_u_x, _, _ = make_exact_heat_field()

    derivatives = compute_spectral_fd_derivatives(field, max_spatial_order=np.int64(1))

    assert set(derivatives.derivatives) == {"u_t", "u_x"}
    assert derivatives.config["spatial_max_order"] == 1
    np.testing.assert_allclose(derivatives.derivatives["u_x"], expected_u_x, atol=1e-10, rtol=1e-10)


def test_spectral_fd_third_order_matches_exact_fourier_derivative() -> None:
    field, _, _, expected_u_xxx = make_exact_heat_field()

    derivatives = compute_spectral_fd_derivatives(field, max_spatial_order=3)

    assert set(derivatives.derivatives) == {"u_t", "u_x", "u_xx", "u_xxx"}
    assert derivatives.config["spatial_max_order"] == 3
    np.testing.assert_allclose(derivatives.derivatives["u_xxx"], expected_u_xxx, atol=1e-9, rtol=1e-9)


@pytest.mark.parametrize("max_spatial_order", [True, np.bool_(False), 0, 4, -1, 1.0, np.float64(2.0), "3"])
def test_spectral_fd_rejects_invalid_max_spatial_order(max_spatial_order: object) -> None:
    field, _, _, _ = make_exact_heat_field()

    with pytest.raises(ScopeValidationError, match="max_spatial_order"):
        compute_spectral_fd_derivatives(field, max_spatial_order=max_spatial_order)  # type: ignore[arg-type]
