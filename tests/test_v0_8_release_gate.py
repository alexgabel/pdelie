from __future__ import annotations

import importlib
from functools import lru_cache
from pathlib import Path

import numpy as np
import pytest

import pdelie
from pdelie.data import generate_burgers_1d_field_batch, generate_heat_1d_field_batch
from pdelie.residuals import evaluate_weak_burgers_residual, evaluate_weak_heat_residual
from tests._helpers.weak_robustness_benchmark import (
    IMPORTED_PARITY_FLOAT_KEYS,
    IMPORTED_PARITY_STRUCTURAL_KEYS,
    run_imported_weak_robustness_benchmark,
    run_native_weak_robustness_benchmark,
)


_EXPECTED_REPORT_KEYS = {
    "equation",
    "equation_form",
    "method_family",
    "window_residuals",
    "time_window_centers",
    "x_window_centers",
    "normalization",
    "diagnostics",
}
_EXPECTED_DIAGNOSTIC_KEYS = {
    "strong_form",
    "weak_form",
    "diffusivity",
    "time_window_size",
    "x_window_size",
    "time_window_stride",
    "x_window_stride",
    "quadrature",
    "test_function",
    "periodic_x_wrapping",
    "window_counts",
    "max_abs_residual",
    "l2_residual",
}
_IMPORTED_CASES = (("heat", "noisy"), ("burgers", "coarse"))


@lru_cache(maxsize=1)
def _cached_native_benchmark() -> dict[str, dict[str, dict[str, object]]]:
    return run_native_weak_robustness_benchmark()


@lru_cache(maxsize=1)
def _cached_numpy_imported_benchmark() -> dict[str, dict[str, dict[str, object]]]:
    return run_imported_weak_robustness_benchmark(importer_name="from_numpy")


@lru_cache(maxsize=1)
def _cached_xarray_imported_benchmark() -> dict[str, dict[str, dict[str, object]]]:
    return run_imported_weak_robustness_benchmark(importer_name="from_xarray")


def _api_stability_text() -> str:
    return (Path(__file__).resolve().parents[1] / "docs/specs/API_STABILITY.md").read_text(encoding="utf-8")


def _assert_report_structure(
    report: dict[str, object],
    *,
    equation: str,
    equation_form: str,
) -> None:
    assert set(report) == _EXPECTED_REPORT_KEYS
    assert report["equation"] == equation
    assert report["equation_form"] == equation_form
    assert report["method_family"] == "local_separable_quartic_bump_trapezoid_v1"
    assert report["normalization"] == "none"

    diagnostics = report["diagnostics"]
    assert isinstance(diagnostics, dict)
    assert set(diagnostics) == _EXPECTED_DIAGNOSTIC_KEYS

    window_residuals = np.asarray(report["window_residuals"], dtype=float)
    time_window_centers = np.asarray(report["time_window_centers"], dtype=float)
    x_window_centers = np.asarray(report["x_window_centers"], dtype=float)

    assert window_residuals.ndim == 4
    assert window_residuals.shape[0] == 1
    assert window_residuals.shape[1] == time_window_centers.size
    assert window_residuals.shape[2] == x_window_centers.size
    assert window_residuals.shape[3] == 1
    assert np.all(np.isfinite(window_residuals))
    assert np.all(np.isfinite(time_window_centers))
    assert np.all(np.isfinite(x_window_centers))
    assert np.isfinite(float(diagnostics["max_abs_residual"]))
    assert np.isfinite(float(diagnostics["l2_residual"]))


def _assert_imported_parity(native_summary: dict[str, object], imported_summary: dict[str, object]) -> None:
    for key in IMPORTED_PARITY_STRUCTURAL_KEYS:
        assert imported_summary[key] == native_summary[key]
    for key in IMPORTED_PARITY_FLOAT_KEYS:
        np.testing.assert_allclose(
            float(imported_summary[key]),
            float(native_summary[key]),
            rtol=1e-9,
            atol=1e-12,
        )


def test_v0_8_release_gate_runtime_surface_and_api_stability_doc_are_aligned() -> None:
    residuals_module = importlib.import_module("pdelie.residuals")
    data_module = importlib.import_module("pdelie.data")
    api_stability = _api_stability_text()

    assert hasattr(residuals_module, "evaluate_weak_heat_residual")
    assert hasattr(residuals_module, "evaluate_weak_burgers_residual")
    assert not hasattr(pdelie, "evaluate_weak_heat_residual")
    assert not hasattr(pdelie, "evaluate_weak_burgers_residual")
    assert not hasattr(residuals_module, "compute_weak_derivatives")
    assert not hasattr(residuals_module, "evaluate_weak_kdv_residual")
    assert not hasattr(residuals_module, "WeakHeatResidualEvaluator")
    assert not hasattr(residuals_module, "WeakBurgersResidualEvaluator")
    assert not hasattr(residuals_module, "WeakKdVResidualEvaluator")
    assert hasattr(residuals_module, "KdVResidualEvaluator")
    assert not hasattr(residuals_module, "KDVResidualEvaluator")
    assert not hasattr(residuals_module, "KdvResidualEvaluator")
    assert not hasattr(pdelie, "generate_kdv_1d_field_batch")
    assert not hasattr(pdelie, "KdVResidualEvaluator")
    assert not hasattr(pdelie, "run_kdv_vertical_slice_example")
    assert not hasattr(data_module, "sample_kdv_mode_coefficients")

    assert "pdelie.residuals.evaluate_weak_heat_residual" in api_stability
    assert "pdelie.residuals.evaluate_weak_burgers_residual" in api_stability
    assert "weak-form derivatives and weak-form methods beyond the frozen `v0.8` weak residual report slice" in api_stability
    assert "compute_weak_derivatives" not in api_stability
    assert "evaluate_weak_kdv_residual" not in api_stability


def test_v0_8_release_gate_clean_reports_are_deterministic_and_structurally_valid() -> None:
    heat = generate_heat_1d_field_batch(batch_size=1, num_times=5, num_points=9, seed=8100)
    burgers = generate_burgers_1d_field_batch(batch_size=1, num_times=5, num_points=9, seed=8200)

    first_heat = evaluate_weak_heat_residual(heat)
    second_heat = evaluate_weak_heat_residual(heat)
    first_burgers = evaluate_weak_burgers_residual(burgers)
    second_burgers = evaluate_weak_burgers_residual(burgers)

    _assert_report_structure(first_heat, equation="heat_1d", equation_form="nonconservative")
    _assert_report_structure(first_burgers, equation="burgers_1d", equation_form="conservative")

    np.testing.assert_allclose(first_heat["window_residuals"], second_heat["window_residuals"], rtol=0.0, atol=0.0)
    np.testing.assert_allclose(first_burgers["window_residuals"], second_burgers["window_residuals"], rtol=0.0, atol=0.0)
    np.testing.assert_allclose(first_heat["time_window_centers"], second_heat["time_window_centers"], rtol=0.0, atol=0.0)
    np.testing.assert_allclose(first_burgers["time_window_centers"], second_burgers["time_window_centers"], rtol=0.0, atol=0.0)


def test_v0_8_release_gate_representative_typed_rejections_remain_in_place() -> None:
    heat = generate_heat_1d_field_batch(batch_size=1, num_times=5, num_points=9, seed=8300)

    with pytest.raises(pdelie.SchemaValidationError, match="FieldBatch input"):
        evaluate_weak_heat_residual(object())

    heat.metadata["boundary_conditions"] = {"x": "dirichlet"}
    with pytest.raises(pdelie.ScopeValidationError, match="periodic boundary conditions in x"):
        evaluate_weak_heat_residual(heat)


def test_v0_8_release_gate_clean_benchmark_baseline_holds() -> None:
    benchmark = _cached_native_benchmark()

    for pde_name in ("heat", "burgers"):
        clean = benchmark[pde_name]["clean"]
        assert clean["strong"]["contract_stable"] is True
        assert clean["weak"]["contract_stable"] is True
        assert float(clean["strong"]["first_epsilon_wrong_to_fitted_ratio"]) >= 5.0
        assert float(clean["weak"]["first_epsilon_wrong_to_fitted_ratio"]) >= 5.0


def test_v0_8_release_gate_degraded_signal_interpretation_holds_without_overfitting_condition() -> None:
    benchmark = _cached_native_benchmark()

    for pde_name in ("heat", "burgers"):
        degraded_with_signal = [
            benchmark[pde_name][condition]
            for condition in ("noisy", "coarse")
            if benchmark[pde_name][condition]["comparison"]["weak_has_robustness_signal"]
        ]
        assert degraded_with_signal, f"{pde_name} must retain at least one degraded weak robustness signal."

        for case in degraded_with_signal:
            comparison = case["comparison"]
            weak = case["weak"]
            assert comparison["robustness_signal_source"] in {"contract_stability_signal", "separation_signal"}
            assert weak["contract_mode"] in {"in_tolerance_fit", "canonical_fallback"}
            if weak["contract_mode"] == "canonical_fallback":
                assert weak["reference_fallback_used"] is True
                assert weak["fallback_reason"] is not None


def test_v0_8_release_gate_imported_subset_matches_native_summary_fields() -> None:
    native = _cached_native_benchmark()
    imported = _cached_numpy_imported_benchmark()

    for pde_name, condition in _IMPORTED_CASES:
        native_case = native[pde_name][condition]
        imported_case = imported[pde_name][condition]
        _assert_imported_parity(native_case["strong"], imported_case["strong"])
        _assert_imported_parity(native_case["weak"], imported_case["weak"])


def test_v0_8_release_gate_optional_xarray_imported_subset_matches_native_summary_fields() -> None:
    pytest.importorskip(
        "xarray",
        reason="xarray is required for the optional v0.8 release-gate imported parity slice.",
    )
    native = _cached_native_benchmark()
    imported = _cached_xarray_imported_benchmark()

    for pde_name, condition in _IMPORTED_CASES:
        native_case = native[pde_name][condition]
        imported_case = imported[pde_name][condition]
        _assert_imported_parity(native_case["strong"], imported_case["strong"])
        _assert_imported_parity(native_case["weak"], imported_case["weak"])
