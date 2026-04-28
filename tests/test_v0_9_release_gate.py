from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pytest

import pdelie
from pdelie.data import (
    from_numpy,
    generate_burgers_1d_field_batch,
    generate_heat_1d_field_batch,
    generate_kdv_1d_field_batch,
    split_batch_train_heldout,
)
from pdelie.derivatives import compute_spectral_fd_derivatives
from pdelie.examples import run_kdv_vertical_slice_example
from pdelie.residuals import (
    KdVResidualEvaluator,
    evaluate_weak_burgers_residual,
    evaluate_weak_heat_residual,
)
from pdelie.symmetry.fitting import fit_translation_generator
from pdelie.symmetry.parameterization import translation_span_distance
from pdelie.verification import verify_translation_generator


def _api_stability_text() -> str:
    return (Path(__file__).resolve().parents[1] / "docs/specs/API_STABILITY.md").read_text(encoding="utf-8")


def _import_from_numpy(field):
    return from_numpy(
        field.values[..., 0],
        dims=("batch", "time", "x"),
        coords={"time": field.coords["time"], "x": field.coords["x"]},
        var_name=field.var_names[0],
        metadata=field.metadata,
        mask=None if field.mask is None else field.mask[..., 0],
        preprocess_log=field.preprocess_log,
    )


def _import_from_xarray(field):
    xr = pytest.importorskip(
        "xarray",
        reason="xarray is required for the optional v0.9 release-gate imported parity slice.",
    )
    coords = {
        "batch": np.arange(field.values.shape[0], dtype=int),
        "time": field.coords["time"],
        "x": field.coords["x"],
    }
    data_array = xr.DataArray(
        field.values[..., 0],
        dims=("batch", "time", "x"),
        coords=coords,
        name=field.var_names[0],
    )
    return importlib.import_module("pdelie.data").from_xarray(
        data_array,
        metadata=field.metadata,
        preprocess_log=field.preprocess_log,
    )


def _kdv_train_heldout():
    field = generate_kdv_1d_field_batch(batch_size=5, seed=9001)
    return split_batch_train_heldout(field, train_size=2, seed=9002)


def _run_kdv_summary(training, heldout) -> dict[str, object]:
    evaluator = KdVResidualEvaluator()
    derivatives = compute_spectral_fd_derivatives(training, max_spatial_order=3)
    residual = evaluator.evaluate(training, derivatives)
    generator = fit_translation_generator(training, evaluator, epsilon=1e-4)
    report = verify_translation_generator(heldout, generator, evaluator)
    return {
        "derivative_keys": set(derivatives.derivatives),
        "derivative_config": derivatives.config,
        "backend": derivatives.backend,
        "residual_equation": residual.diagnostics["equation"],
        "max_abs_residual": float(residual.diagnostics["max_abs_residual"]),
        "rms_residual": float(residual.diagnostics["rms_residual"]),
        "parameterization": generator.parameterization,
        "coefficients": generator.coefficients,
        "fit_mode": generator.diagnostics["fit_mode"],
        "reference_fallback_used": generator.diagnostics["reference_fallback_used"],
        "span_distance": float(translation_span_distance(generator.coefficients)),
        "verification_classification": report.classification,
        "transform_mode": report.diagnostics["transform_mode"],
        "epsilon_values": report.epsilon_values,
        "error_curve": report.error_curve,
    }


def _assert_kdv_summary_parity(native: dict[str, object], imported: dict[str, object]) -> None:
    for key in (
        "derivative_keys",
        "derivative_config",
        "backend",
        "residual_equation",
        "parameterization",
        "fit_mode",
        "reference_fallback_used",
        "verification_classification",
        "transform_mode",
    ):
        assert imported[key] == native[key]
    for key in (
        "max_abs_residual",
        "rms_residual",
        "coefficients",
        "span_distance",
        "epsilon_values",
        "error_curve",
    ):
        np.testing.assert_allclose(imported[key], native[key], rtol=1e-9, atol=1e-12)


def test_v0_9_release_gate_runtime_surface_and_api_stability_doc_are_aligned() -> None:
    data_module = importlib.import_module("pdelie.data")
    residuals_module = importlib.import_module("pdelie.residuals")
    examples_module = importlib.import_module("pdelie.examples")
    api_stability = _api_stability_text()

    assert hasattr(data_module, "generate_kdv_1d_field_batch")
    assert hasattr(residuals_module, "KdVResidualEvaluator")
    assert hasattr(examples_module, "run_kdv_vertical_slice_example")
    assert not hasattr(pdelie, "generate_kdv_1d_field_batch")
    assert not hasattr(pdelie, "KdVResidualEvaluator")
    assert not hasattr(pdelie, "run_kdv_vertical_slice_example")

    assert not hasattr(data_module, "sample_kdv_mode_coefficients")
    assert not hasattr(residuals_module, "evaluate_weak_kdv_residual")
    assert not hasattr(residuals_module, "WeakKdVResidualEvaluator")
    assert not hasattr(residuals_module, "compute_weak_derivatives")
    assert not hasattr(residuals_module, "KDVResidualEvaluator")
    assert not hasattr(residuals_module, "KdvResidualEvaluator")

    assert "compute_spectral_fd_derivatives(field, *, max_spatial_order=2)" in api_stability
    assert "pdelie.data.generate_kdv_1d_field_batch" in api_stability
    assert "pdelie.residuals.KdVResidualEvaluator" in api_stability
    assert "no root `pdelie` export" in api_stability
    assert "weak KdV behavior" in api_stability
    assert "compute_weak_derivatives" not in api_stability
    assert "evaluate_weak_kdv_residual" not in api_stability


def test_v0_9_release_gate_representative_kdv_vertical_slice_holds() -> None:
    result = run_kdv_vertical_slice_example()

    assert result["backend"] == "spectral_fd"
    assert result["max_abs_residual"] < 1e-2
    assert result["rms_residual"] < 2e-3
    assert result["mass_drift"] <= 1e-8
    assert result["relative_l2_drift"] <= 5e-3
    assert result["parameterization"] == "polynomial_translation_affine"
    assert result["span_distance"] <= 5e-2
    assert result["error_curve"][0] < 1e-4
    assert result["verification_classification"] != "failed"


@pytest.mark.parametrize("importer", [_import_from_numpy, _import_from_xarray])
def test_v0_9_release_gate_representative_kdv_imported_parity_holds(
    importer: Callable[[Any], Any],
) -> None:
    native_training, native_heldout = _kdv_train_heldout()
    imported_training = importer(native_training)
    imported_heldout = importer(native_heldout)

    assert imported_training.metadata["parameter_tags"] == {"equation": "kdv_normalized"}
    assert imported_heldout.metadata["parameter_tags"] == {"equation": "kdv_normalized"}
    native_summary = _run_kdv_summary(native_training, native_heldout)
    imported_summary = _run_kdv_summary(imported_training, imported_heldout)
    _assert_kdv_summary_parity(native_summary, imported_summary)


def test_v0_9_release_gate_v0_8_weak_report_surface_still_runs() -> None:
    heat = generate_heat_1d_field_batch(batch_size=1, num_times=5, num_points=9, seed=9100)
    burgers = generate_burgers_1d_field_batch(batch_size=1, num_times=5, num_points=9, seed=9101)

    heat_report = evaluate_weak_heat_residual(heat)
    burgers_report = evaluate_weak_burgers_residual(burgers)

    assert heat_report["method_family"] == "local_separable_quartic_bump_trapezoid_v1"
    assert burgers_report["method_family"] == "local_separable_quartic_bump_trapezoid_v1"
    assert heat_report["normalization"] == "none"
    assert burgers_report["normalization"] == "none"
    assert np.all(np.isfinite(heat_report["window_residuals"]))
    assert np.all(np.isfinite(burgers_report["window_residuals"]))
