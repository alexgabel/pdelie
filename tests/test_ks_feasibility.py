from __future__ import annotations

import importlib

import numpy as np

import pdelie
from pdelie.derivatives import compute_spectral_fd_derivatives
from tests._helpers.ks_feasibility import (
    KS_FEASIBILITY_CONFIG,
    compute_mass,
    evaluate_ks_fourier_series,
    generate_ks_feasibility_field_batch,
    sample_ks_mode_coefficients,
)


def test_ks_feasibility_generator_is_reproducible_and_seed_sensitive() -> None:
    first = generate_ks_feasibility_field_batch(seed=11111)
    second = generate_ks_feasibility_field_batch(seed=11111)
    different = generate_ks_feasibility_field_batch(seed=11112)

    np.testing.assert_allclose(first.values, second.values, rtol=0.0, atol=1e-15)
    assert not np.allclose(first.values, different.values, rtol=0.0, atol=0.0)


def test_ks_feasibility_generator_freezes_shape_coordinates_and_metadata() -> None:
    field = generate_ks_feasibility_field_batch()
    batch_size = int(KS_FEASIBILITY_CONFIG["batch_size"])
    num_times = int(KS_FEASIBILITY_CONFIG["num_times"])
    num_points = int(KS_FEASIBILITY_CONFIG["num_points"])
    max_time = float(KS_FEASIBILITY_CONFIG["max_time"])
    domain_length = float(KS_FEASIBILITY_CONFIG["domain_length"])

    assert field.values.shape == (batch_size, num_times, num_points, 1)
    assert field.dims == ("batch", "time", "x", "var")
    assert field.var_names == ["u"]
    assert field.mask is None
    assert field.preprocess_log == []
    np.testing.assert_allclose(field.coords["x"], np.linspace(0.0, domain_length, num_points, endpoint=False))
    np.testing.assert_allclose(field.coords["time"], np.linspace(0.0, max_time, num_times))
    assert field.coords["x"][0] == 0.0
    assert field.coords["x"][-1] == domain_length * (num_points - 1) / num_points
    assert field.coords["time"][0] == 0.0
    assert field.coords["time"][-1] == max_time
    assert field.metadata["boundary_conditions"] == {"x": "periodic"}
    assert field.metadata["grid_type"] == "rectilinear"
    assert field.metadata["grid_regularity"] == "uniform"
    assert field.metadata["coordinate_system"] == "cartesian"
    assert field.metadata["parameter_tags"] == {"equation": "ks_normalized"}
    assert np.all(np.isfinite(field.values))
    field.validate()


def test_ks_feasibility_generator_preserves_zero_mode_and_mass() -> None:
    field = generate_ks_feasibility_field_batch()

    mean_by_batch_time = np.mean(field.values[..., 0], axis=-1)
    mass = compute_mass(field)
    mass_drift = np.max(np.abs(mass - mass[:, [0]]))

    np.testing.assert_allclose(mean_by_batch_time, np.zeros_like(mean_by_batch_time), atol=1e-14, rtol=0.0)
    assert mass_drift <= 1e-8


def test_ks_feasibility_fourier_series_scales_phase_by_domain_length() -> None:
    batch_size = 2
    num_modes = 4
    num_points = 64
    domain_length = 40.0
    amplitude = 0.05
    seed = 11121
    x = np.linspace(0.0, domain_length, num_points, endpoint=False)
    cosine, sine = sample_ks_mode_coefficients(
        batch_size=batch_size,
        num_modes=num_modes,
        seed=seed,
        amplitude=amplitude,
    )

    values = evaluate_ks_fourier_series(
        x=x,
        domain_length=domain_length,
        cosine_coefficients=cosine,
        sine_coefficients=sine,
    )

    modes = np.arange(1, num_modes + 1, dtype=float)
    phase = (2.0 * np.pi / domain_length) * x
    expected = np.sum(
        cosine[:, :, None] * np.cos(np.outer(modes, phase))[None, :, :]
        + sine[:, :, None] * np.sin(np.outer(modes, phase))[None, :, :],
        axis=1,
    )
    raw_x_expected = np.sum(
        cosine[:, :, None] * np.cos(np.outer(modes, x))[None, :, :]
        + sine[:, :, None] * np.sin(np.outer(modes, x))[None, :, :],
        axis=1,
    )

    np.testing.assert_allclose(values, expected, atol=1e-14, rtol=1e-14)
    assert not np.allclose(values, raw_x_expected, atol=1e-12, rtol=1e-12)


def test_ks_feasibility_uses_public_fourth_derivative_sign_convention() -> None:
    field = generate_ks_feasibility_field_batch(num_times=3, max_time=0.01)

    derivatives = compute_spectral_fd_derivatives(field, max_spatial_order=4)

    assert set(derivatives.derivatives) == {"u_t", "u_x", "u_xx", "u_xxx", "u_xxxx"}
    assert derivatives.config["spatial_max_order"] == 4
    residual = (
        derivatives.derivatives["u_t"]
        + field.values * derivatives.derivatives["u_x"]
        + derivatives.derivatives["u_xx"]
        + derivatives.derivatives["u_xxxx"]
    )
    assert float(np.sqrt(np.mean(np.square(residual)))) < 1e-2


def test_ks_feasibility_helper_adds_no_public_ks_surface() -> None:
    data_module = importlib.import_module("pdelie.data")
    residuals_module = importlib.import_module("pdelie.residuals")

    assert not hasattr(pdelie, "generate_ks_feasibility_field_batch")
    assert not hasattr(pdelie, "generate_ks_1d_field_batch")
    assert not hasattr(pdelie, "KSResidualEvaluator")
    assert not hasattr(data_module, "generate_ks_feasibility_field_batch")
    assert not hasattr(data_module, "generate_ks_1d_field_batch")
    assert not hasattr(residuals_module, "KSResidualEvaluator")
    assert not hasattr(residuals_module, "KuramotoSivashinskyResidualEvaluator")
