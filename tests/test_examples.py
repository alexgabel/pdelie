from __future__ import annotations

import json
import subprocess
import sys

import numpy as np

import pdelie
from pdelie.examples import run_heat_vertical_slice_example, run_kdv_vertical_slice_example


def test_heat_vertical_slice_example_runs_end_to_end() -> None:
    result = run_heat_vertical_slice_example()
    assert result["backend"] == "spectral_fd"
    assert result["parameterization"] == "polynomial_translation_affine"
    assert result["verification_classification"] == "exact"


def test_heat_vertical_slice_example_is_deterministic() -> None:
    first = run_heat_vertical_slice_example()
    second = run_heat_vertical_slice_example()

    assert first["verification_classification"] == second["verification_classification"]
    assert first["backend"] == second["backend"]
    assert first["parameterization"] == second["parameterization"]
    assert first["coefficients"] == second["coefficients"]
    assert first["error_curve"] == second["error_curve"]


def test_kdv_vertical_slice_example_runs_end_to_end_and_is_json_serializable() -> None:
    result = run_kdv_vertical_slice_example()

    assert json.loads(json.dumps(result)) == result
    assert result["backend"] == "spectral_fd"
    assert result["parameterization"] == "polynomial_translation_affine"
    assert result["fit_mode"] == "svd"
    assert result["reference_fallback_used"] is False
    assert result["verification_classification"] != "failed"
    assert result["max_abs_residual"] < 1e-2
    assert result["rms_residual"] < 2e-3
    assert result["mass_drift"] <= 1e-8
    assert result["relative_l2_drift"] <= 5e-3
    assert result["span_distance"] <= 5e-2
    assert result["error_curve"][0] < 1e-4
    assert not hasattr(pdelie, "run_kdv_vertical_slice_example")


def test_kdv_vertical_slice_example_is_deterministic() -> None:
    first = run_kdv_vertical_slice_example()
    second = run_kdv_vertical_slice_example()

    for key in (
        "backend",
        "parameterization",
        "fit_mode",
        "reference_fallback_used",
        "verification_classification",
    ):
        assert first[key] == second[key]
    for key in (
        "max_abs_residual",
        "rms_residual",
        "mass_drift",
        "relative_l2_drift",
        "span_distance",
        "coefficients",
        "epsilon_values",
        "error_curve",
    ):
        np.testing.assert_allclose(np.asarray(first[key], dtype=float), np.asarray(second[key], dtype=float))


def test_kdv_vertical_slice_module_prints_json_only() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "pdelie.examples.kdv_vertical_slice"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stderr == ""
    parsed = json.loads(completed.stdout)
    assert parsed["backend"] == "spectral_fd"
    assert parsed["verification_classification"] != "failed"
