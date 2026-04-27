from __future__ import annotations

import importlib
from functools import lru_cache

import numpy as np
import pytest

import pdelie
from tests._helpers.weak_robustness_benchmark import (
    COMPARISON_SUMMARY_KEYS,
    IMPORTED_PARITY_FLOAT_KEYS,
    IMPORTED_PARITY_STRUCTURAL_KEYS,
    PATH_SUMMARY_FLOAT_KEYS,
    PATH_SUMMARY_STRUCTURAL_KEYS,
    run_imported_weak_robustness_benchmark,
    run_native_weak_robustness_benchmark,
)


_SUMMARY_KEYS = set(PATH_SUMMARY_STRUCTURAL_KEYS) | set(PATH_SUMMARY_FLOAT_KEYS)
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


def _assert_path_summary_schema(summary: dict[str, object], *, path: str, pde_name: str, condition: str) -> None:
    assert set(summary) == _SUMMARY_KEYS
    assert summary["path"] == path
    assert summary["pde"] == pde_name
    assert summary["condition"] == condition
    assert isinstance(summary["contract_stable"], bool)
    assert isinstance(summary["deterministic"], bool)
    assert summary["contract_mode"] in {"in_tolerance_fit", "canonical_fallback", "out_of_tolerance"}
    assert summary["wrong_generator_description"] == "x-basis affine non-translation control"
    for key in PATH_SUMMARY_FLOAT_KEYS:
        assert np.isfinite(float(summary[key]))


def _assert_comparison_summary_schema(summary: dict[str, object]) -> None:
    assert set(summary) == set(COMPARISON_SUMMARY_KEYS)
    assert summary["weak_contract_mode"] in {"in_tolerance_fit", "canonical_fallback", "out_of_tolerance"}
    assert summary["strong_contract_mode"] in {"in_tolerance_fit", "canonical_fallback", "out_of_tolerance"}
    assert summary["robustness_signal_source"] in {"contract_stability_signal", "separation_signal", "none"}
    assert isinstance(summary["weak_contract_stable"], bool)
    assert isinstance(summary["strong_contract_stable"], bool)
    assert isinstance(summary["weak_has_robustness_signal"], bool)
    assert np.isfinite(float(summary["weak_ratio"]))
    assert np.isfinite(float(summary["strong_ratio"]))


def _assert_summary_match(first: dict[str, object], second: dict[str, object]) -> None:
    for key in PATH_SUMMARY_STRUCTURAL_KEYS:
        assert first[key] == second[key]
    for key in PATH_SUMMARY_FLOAT_KEYS:
        np.testing.assert_allclose(float(first[key]), float(second[key]), rtol=1e-9, atol=1e-12)


def _assert_comparison_match(first: dict[str, object], second: dict[str, object]) -> None:
    assert first["weak_contract_mode"] == second["weak_contract_mode"]
    assert first["strong_contract_mode"] == second["strong_contract_mode"]
    assert first["weak_contract_stable"] == second["weak_contract_stable"]
    assert first["strong_contract_stable"] == second["strong_contract_stable"]
    assert first["robustness_signal_source"] == second["robustness_signal_source"]
    assert first["weak_has_robustness_signal"] == second["weak_has_robustness_signal"]
    np.testing.assert_allclose(
        [float(first["weak_ratio"]), float(first["strong_ratio"])],
        [float(second["weak_ratio"]), float(second["strong_ratio"])],
        rtol=1e-9,
        atol=1e-12,
    )


def _assert_imported_path_parity(native_summary: dict[str, object], imported_summary: dict[str, object]) -> None:
    for key in IMPORTED_PARITY_STRUCTURAL_KEYS:
        assert imported_summary[key] == native_summary[key]
    for key in IMPORTED_PARITY_FLOAT_KEYS:
        np.testing.assert_allclose(
            float(imported_summary[key]),
            float(native_summary[key]),
            rtol=1e-9,
            atol=1e-12,
        )


def test_native_weak_robustness_benchmark_is_reproducible_and_has_frozen_summary_schema() -> None:
    first = run_native_weak_robustness_benchmark()
    second = run_native_weak_robustness_benchmark()

    for pde_name in ("heat", "burgers"):
        for condition in ("clean", "noisy", "coarse"):
            first_case = first[pde_name][condition]
            second_case = second[pde_name][condition]
            _assert_path_summary_schema(first_case["strong"], path="strong", pde_name=pde_name, condition=condition)
            _assert_path_summary_schema(first_case["weak"], path="weak", pde_name=pde_name, condition=condition)
            _assert_comparison_summary_schema(first_case["comparison"])
            _assert_summary_match(first_case["strong"], second_case["strong"])
            _assert_summary_match(first_case["weak"], second_case["weak"])
            _assert_comparison_match(first_case["comparison"], second_case["comparison"])
            assert first_case["strong"]["deterministic"] is True
            assert first_case["weak"]["deterministic"] is True


def test_clean_heat_benchmark_meets_the_frozen_clean_baseline() -> None:
    result = _cached_native_benchmark()["heat"]["clean"]

    assert result["strong"]["contract_stable"] is True
    assert result["weak"]["contract_stable"] is True
    assert float(result["strong"]["first_epsilon_wrong_to_fitted_ratio"]) >= 5.0
    assert float(result["weak"]["first_epsilon_wrong_to_fitted_ratio"]) >= 5.0


def test_clean_burgers_benchmark_meets_the_frozen_clean_baseline() -> None:
    result = _cached_native_benchmark()["burgers"]["clean"]

    assert result["strong"]["contract_stable"] is True
    assert result["weak"]["contract_stable"] is True
    assert float(result["strong"]["first_epsilon_wrong_to_fitted_ratio"]) >= 5.0
    assert float(result["weak"]["first_epsilon_wrong_to_fitted_ratio"]) >= 5.0


def test_degraded_heat_has_a_weak_robustness_signal() -> None:
    benchmark = _cached_native_benchmark()["heat"]
    assert any(
        benchmark[condition]["comparison"]["weak_has_robustness_signal"]
        for condition in ("noisy", "coarse")
    )


def test_degraded_burgers_has_a_weak_robustness_signal() -> None:
    benchmark = _cached_native_benchmark()["burgers"]
    assert any(
        benchmark[condition]["comparison"]["weak_has_robustness_signal"]
        for condition in ("noisy", "coarse")
    )


def test_from_numpy_imported_subset_matches_native_summary_fields() -> None:
    native = _cached_native_benchmark()
    imported = _cached_numpy_imported_benchmark()

    for pde_name, condition in _IMPORTED_CASES:
        native_case = native[pde_name][condition]
        imported_case = imported[pde_name][condition]
        _assert_imported_path_parity(native_case["strong"], imported_case["strong"])
        _assert_imported_path_parity(native_case["weak"], imported_case["weak"])


def test_from_xarray_imported_subset_matches_native_summary_fields() -> None:
    pytest.importorskip(
        "xarray",
        reason="xarray is required for the optional M4 imported benchmark parity slice.",
    )
    native = _cached_native_benchmark()
    imported = _cached_xarray_imported_benchmark()

    for pde_name, condition in _IMPORTED_CASES:
        native_case = native[pde_name][condition]
        imported_case = imported[pde_name][condition]
        _assert_imported_path_parity(native_case["strong"], imported_case["strong"])
        _assert_imported_path_parity(native_case["weak"], imported_case["weak"])


def test_m4_benchmark_adds_no_public_surface() -> None:
    residuals_module = importlib.import_module("pdelie.residuals")
    data_module = importlib.import_module("pdelie.data")

    assert not hasattr(pdelie, "run_native_weak_robustness_benchmark")
    assert not hasattr(pdelie, "run_imported_weak_robustness_benchmark")
    assert not hasattr(residuals_module, "run_native_weak_robustness_benchmark")
    assert not hasattr(residuals_module, "run_imported_weak_robustness_benchmark")
    assert not hasattr(data_module, "run_native_weak_robustness_benchmark")
    assert not hasattr(data_module, "run_imported_weak_robustness_benchmark")
