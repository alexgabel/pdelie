from __future__ import annotations

import importlib

import numpy as np
import pytest

import pdelie
from tests._helpers.kdv_feasibility import (
    KDV_FEASIBILITY_CONFIG,
    compute_kdv_feasibility_derivatives,
    compute_l2_norm,
    compute_mass,
    evaluate_kdv_feasibility_residual,
    exact_fourier_third_derivative,
    generate_kdv_1d_field_batch,
    sample_kdv_mode_coefficients,
)


def _generation_kwargs() -> dict[str, object]:
    return {
        key: KDV_FEASIBILITY_CONFIG[key]
        for key in ("batch_size", "num_times", "num_points", "max_time", "num_modes", "amplitude", "num_substeps")
    }


def test_kdv_fourier_mode_third_derivative_matches_exact() -> None:
    x = np.linspace(
        0.0,
        float(KDV_FEASIBILITY_CONFIG["domain_length"]),
        int(KDV_FEASIBILITY_CONFIG["num_points"]),
        endpoint=False,
        dtype=float,
    )
    t = np.linspace(0.0, 0.1, 3, dtype=float)
    cosine, sine = sample_kdv_mode_coefficients(
        batch_size=1,
        num_modes=2,
        seed=7,
        amplitude=0.08,
    )
    spatial_values = np.sum(
        cosine[:, :, None] * np.cos(np.outer(np.arange(1, 3, dtype=float), x))[None, :, :]
        + sine[:, :, None] * np.sin(np.outer(np.arange(1, 3, dtype=float), x))[None, :, :],
        axis=1,
    )
    values = np.repeat(spatial_values[:, None, :, None], t.size, axis=1)
    field = pdelie.FieldBatch(
        values=values,
        dims=("batch", "time", "x", "var"),
        coords={"time": t, "x": x},
        var_names=["u"],
        metadata={
            "boundary_conditions": {"x": "periodic"},
            "coordinate_system": "cartesian",
            "grid_regularity": "uniform",
            "grid_type": "rectilinear",
            "parameter_tags": {"equation": "kdv_normalized"},
        },
        preprocess_log=[],
    )

    derivatives = compute_kdv_feasibility_derivatives(field)
    expected = exact_fourier_third_derivative(x=x, cosine_coefficients=cosine, sine_coefficients=sine)
    np.testing.assert_allclose(
        derivatives.derivatives["u_xxx"][:, 0, :, 0],
        expected,
        atol=1e-9,
        rtol=1e-9,
    )


def test_kdv_field_generation_is_reproducible_and_shape_valid() -> None:
    first = generate_kdv_1d_field_batch(seed=11, **_generation_kwargs())
    second = generate_kdv_1d_field_batch(seed=11, **_generation_kwargs())

    np.testing.assert_allclose(first.values, second.values)
    assert first.dims == ("batch", "time", "x", "var")
    assert first.var_names == ["u"]
    assert first.metadata["boundary_conditions"] == {"x": "periodic"}
    assert first.metadata["grid_regularity"] == "uniform"
    assert first.metadata["grid_type"] == "rectilinear"


def test_kdv_residual_is_near_zero_on_clean_short_horizon_data() -> None:
    field = generate_kdv_1d_field_batch(seed=13, **_generation_kwargs())
    residual = evaluate_kdv_feasibility_residual(field)

    assert residual.definition_type == "analytic"
    assert residual.normalization == "none"
    assert np.max(np.abs(residual.residual)) < 1e-2


def test_kdv_short_horizon_mass_and_l2_drift_are_small() -> None:
    field = generate_kdv_1d_field_batch(seed=17, **_generation_kwargs())

    mass = compute_mass(field)
    l2 = compute_l2_norm(field)
    mass_drift = np.max(np.abs(mass - mass[:, [0]]))
    relative_l2_drift = np.max(np.abs(l2 - l2[:, [0]]) / np.maximum(np.abs(l2[:, [0]]), 1e-12))

    assert mass_drift <= 1e-8
    assert relative_l2_drift <= 5e-3


def test_m4_kdv_feasibility_adds_no_stable_surface() -> None:
    assert not hasattr(pdelie, "KdVResidualEvaluator")
    assert not hasattr(pdelie, "generate_kdv_1d_field_batch")

    data_module = importlib.import_module("pdelie.data")
    residuals_module = importlib.import_module("pdelie.residuals")
    assert not hasattr(data_module, "generate_kdv_1d_field_batch")
    assert not hasattr(residuals_module, "KdVResidualEvaluator")
